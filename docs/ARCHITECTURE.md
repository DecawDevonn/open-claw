# System Architecture

## Overview

OpenClaw / Devonn.AI is a Python/Flask REST API for managing AI agent workforces, enriched with a full
integration layer for AI/NLP, voice, semantic search, authentication, and third-party automation.

```
┌─────────────────────────────────────────────────────────────┐
│                       HTTP Clients                          │
│           (curl, SDK, web dashboard, browser ext.)          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│              nginx / Load Balancer                          │
│            (TLS termination, routing)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│            Flask Application (Gunicorn)                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │                  create_app()                      │     │
│  │                                                    │     │
│  │  Core:          /api/agents   /api/tasks           │     │
│  │                 /api/health   /api/status          │     │
│  │                 /api/workforce/*                   │     │
│  │                                                    │     │
│  │  Auth:          /api/auth/register                 │     │
│  │                 /api/auth/token                    │     │
│  │                 /api/auth/me                       │     │
│  │                 /api/auth/revoke                   │     │
│  │                                                    │     │
│  │  AI / NLP:      /api/ai/complete                   │     │
│  │                 /api/ai/chat  (Sapphire Wrapper)   │     │
│  │                 /api/ai/embed                      │     │
│  │                 /api/ai/image                      │     │
│  │                 /api/ai/transcribe                 │     │
│  │                 /api/ai/translate                  │     │
│  │                 /api/ai/hf                         │     │
│  │                                                    │     │
│  │  Memory:        /api/memory/save                   │     │
│  │                 /api/memory/search                 │     │
│  │                 /api/memory/list                   │     │
│  │                 /api/memory/reflect                │     │
│  │                 /api/memory/<id>  DELETE           │     │
│  │                                                    │     │
│  │  Voice:         /api/voice/tts                     │     │
│  │                 /api/voice/stt                     │     │
│  │                 /api/voice/voices                  │     │
│  │                                                    │     │
│  │  Search:        /api/search/vector/upsert          │     │
│  │                 /api/search/vector/query           │     │
│  │                 /api/search/web                    │     │
│  │                 /api/search/algolia                │     │
│  │                                                    │     │
│  │  Integrations:  /api/integrations/webhook          │     │
│  │                 /api/integrations/webhook/verify   │     │
│  │                 /api/integrations/airtable/<table> │     │
│  │                 /api/integrations/sheets/append    │     │
│  │                 /api/integrations/services         │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Service Layer                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │  AIService   │ │ AuthService  │ │   VoiceService   │    │
│  │  (OpenAI,    │ │  (PyJWT,     │ │ (ElevenLabs TTS, │    │
│  │  HuggingFace,│ │  revocation) │ │  AssemblyAI STT) │    │
│  │  Stability,  │ └──────────────┘ └──────────────────┘    │
│  │  DeepL)      │ ┌──────────────┐ ┌──────────────────┐    │
│  └──────────────┘ │SearchService │ │IntegrationsService│   │
│                   │ (Pinecone,   │ │ (Webhook relay,  │    │
│                   │  SerpAPI,    │ │  Airtable,       │    │
│                   │  Algolia)    │ │  Google Sheets)  │    │
│                   └──────────────┘ └──────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    openclaw/config.py  (Settings — all env vars)     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Storage Layer                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │  In-Memory Dict      │  │  MongoStorage            │     │
│  │  (per-app instance,  │  │  (production,            │     │
│  │   test-safe)         │  │   implements base.py)    │     │
│  └──────────────────────┘  └──────────────────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  External Services (called via HTTPS from Service Layer)    │
│                                                             │
│  AI:      OpenAI · HuggingFace · StabilityAI · DeepL       │
│  Voice:   ElevenLabs · AssemblyAI                          │
│  Search:  Pinecone · SerpAPI · Algolia                     │
│  Data:    Airtable · Google Sheets · MongoDB               │
│  Monitor: Sentry · Telegram · Slack · Discord              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### Flask Application (`app.py`)

Uses the **application factory pattern** (`create_app()`):
- Per-call in-memory storage ensures full test isolation
- All service instances created inside the factory with settings from `openclaw/config.py`
- `AuthService` registered on `app.extensions["auth_service"]` for the `require_auth` decorator

### Configuration (`openclaw/config.py`)

Single `Settings` dataclass loaded from environment variables at import time.
Covers ~50 variables across all service categories. `configured_services()` returns
only the names of services with API keys present. `warn_insecure_defaults()` logs
warnings when placeholder values are detected.

### Service Layer (`openclaw/services/`)

| Module | Provider(s) | Key capabilities |
|---|---|---|
| `ai.py` | OpenAI, HuggingFace, StabilityAI, DeepL | Complete, Embed, DALL·E, Whisper, HF inference, Translate, **chat() Cognitive Wrapper** |
| `auth.py` | PyJWT | Issue / verify / revoke JWTs; `require_auth` decorator |
| `voice.py` | ElevenLabs, AssemblyAI | TTS, STT (URL or bytes), speaker labels |
| `search.py` | Pinecone, SerpAPI, Algolia | Vector upsert/query/delete, web search, keyword search |
| `integrations.py` | Webhooks, Airtable, Google Sheets | HMAC-signed relay, list/create records, append rows |
| `monitoring.py` | Sentry | SDK init, structured health payload |
| `sapphire.py` | ChromaDB | Persistent vector memory — save, search, inject, reflect, delete |

Every service method raises `RuntimeError` when its required API key is missing,
which the route handlers catch and return as `503 Service Unavailable`.

### API Endpoints

| Group | Endpoints |
|---|---|
| Agents | `POST/GET /api/agents`, `GET/PUT/DELETE /api/agents/<id>` |
| Tasks | `POST/GET /api/tasks`, `GET/PUT/DELETE /api/tasks/<id>` |
| Workforce | `POST /api/workforce/assign`, `GET /api/workforce/summary` |
| Auth | `POST /api/auth/register`, `POST /api/auth/token`, `GET /api/auth/me`, `POST /api/auth/revoke` |
| AI | `POST /api/ai/complete`, `POST /api/ai/chat`, `POST /api/ai/embed`, `POST /api/ai/image`, `POST /api/ai/transcribe`, `POST /api/ai/translate`, `POST /api/ai/hf` |
| Memory | `POST /api/memory/save`, `POST /api/memory/search`, `GET /api/memory/list`, `POST /api/memory/reflect`, `DELETE /api/memory/<id>` |
| Voice | `POST /api/voice/tts`, `POST /api/voice/stt`, `GET /api/voice/voices` |
| Search | `POST /api/search/vector/upsert`, `POST /api/search/vector/query`, `GET /api/search/web`, `POST /api/search/algolia` |
| Integrations | `POST /api/integrations/webhook`, `POST /api/integrations/webhook/verify`, `GET/POST /api/integrations/airtable/<table>`, `POST /api/integrations/sheets/append`, `GET /api/integrations/services` |
| Leads | `POST/GET /api/leads`, `GET/PUT/DELETE /api/leads/<id>`, score, route, follow-up |
| Comms | `POST /api/comms/sms`, `/whatsapp`, `/call`, `/email` |
| Analytics | `POST/GET /api/analytics/events`, `GET /api/analytics/metrics`, `POST/GET /api/analytics/feedback` |
| Audit | `GET /api/audit` |
| Framework | `POST /api/framework/agents/spawn`, `GET /api/framework/agents`, `POST /api/framework/run`, `GET /api/framework/status` |
| System | `GET /api/health`, `GET /api/status` |

### Storage Layer (`storage/`)

- **In-memory** (dict inside `create_app()`): Default; fast, zero-dependency, per-instance (test-safe).
- **MongoStorage** (`storage/mongo.py`): Drop-in persistent backend implementing `StorageBackend` ABC (`storage/base.py`).

### Authentication

All AI, voice, search, and integration endpoints require a Bearer JWT.
Public endpoints: `/api/health`, `/api/status`, `/api/integrations/services`,
`/api/integrations/webhook/verify`.

---

## Security Model

- **Non-root container**: Docker image runs as user `openclaw`
- **TLS**: Enforced at nginx; the app speaks plain HTTP internally
- **Secrets**: All keys loaded from environment variables via `openclaw/config.py`; never hardcoded
- **JWT**: HS256, configurable expiry; optional JTI revocation via storage backend
- **Webhook signatures**: HMAC-SHA256 on outbound payloads; inbound verification helper
- **JSON injection**: All webhook/notification payloads serialised via `json.dumps` / `python3 json.dumps`
- **Error messages**: Generic messages returned to clients; details logged server-side only

---

## Directory Structure

```
open-claw/
├── app.py                      # Flask application factory + all routes
├── openclaw/
│   ├── __init__.py
│   ├── config.py               # Settings dataclass (all ~55 env vars)
│   ├── framework/
│   │   ├── agent.py            # AgentConfig + Agent dataclasses
│   │   ├── executor.py         # TaskExecutor — runs plans step by step
│   │   ├── memory.py           # AgentMemory — short/long-term in-process store
│   │   ├── planner.py          # MetaPlanner — decomposes goals into TaskPlans
│   │   └── tools.py            # ToolRegistry + save_to_memory tool
│   └── services/
│       ├── __init__.py
│       ├── ai.py               # OpenAI, HuggingFace, StabilityAI, DeepL + chat()
│       ├── auth.py             # JWT issue/verify/revoke + require_auth
│       ├── voice.py            # ElevenLabs TTS, AssemblyAI STT
│       ├── search.py           # Pinecone, SerpAPI, Algolia
│       ├── integrations.py     # Webhook relay, Airtable, Google Sheets
│       ├── monitoring.py       # Sentry init, health payload
│       ├── sapphire.py         # ChromaDB vector memory (Sapphire Protocol)
│       ├── leads.py            # Lead management + AI scoring
│       ├── comms.py            # Twilio SMS/WhatsApp/Call, SendGrid email
│       └── analytics.py        # Event tracking, metrics, feedback
├── storage/
│   ├── base.py                 # StorageBackend ABC
│   └── mongo.py                # MongoDB backend
├── agents/devonn/
│   ├── identity.md             # DEVONN.AI identity profile
│   ├── soul.md                 # Core directives and decision framework
│   ├── agent.md                # Agent execution layer spec
│   ├── task_list.md            # Active task pipeline
│   └── memory.md               # Sapphire memory structure and protocol
├── memory/
│   └── USER.md                 # Operator profile (Wesley Little)
├── tests/
│   ├── test_api.py             # Core agent/task/workforce/status tests
│   ├── test_integrations.py    # Auth/AI/voice/search/integration tests
│   └── test_sapphire.py        # Sapphire memory + Cognitive Wrapper tests
├── docs/                       # Documentation
├── scripts/                    # Utility shell scripts + systemd unit
├── .env.example                # Full credentials template (~55 vars)
├── .github/workflows/          # CI/CD pipelines
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```
