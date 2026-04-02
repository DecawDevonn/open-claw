# OpenClaw

**AI Agent Workforce Management System** — a lightweight REST API for creating, tracking, and
coordinating AI agents and their tasks, with built-in JWT auth, AI/NLP integrations, voice,
semantic search, and the **Sapphire Cognitive Memory** layer (ChromaDB vector store).

[![Build and Test](https://github.com/DecawDevonn/open-claw/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/DecawDevonn/open-claw/actions/workflows/build-and-test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## Quickstart

### Docker (easiest)

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
cp .env.example .env   # edit at minimum SECRET_KEY and JWT_SECRET
docker compose up -d
curl http://localhost:8080/api/health
```

### pip

```bash
pip install open-claw
python -c "from app import create_app; create_app().run(port=8080)"
```

---

## API Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Register user, receive JWT |
| `POST` | `/api/auth/token` | — | Exchange credentials for JWT |
| `GET` | `/api/auth/me` | 🔒 | Current user profile |
| `POST` | `/api/auth/revoke` | 🔒 | Revoke current JWT |
| `POST` | `/api/agents` | 🔒 | Create an agent |
| `GET` | `/api/agents` | 🔒 | List all agents |
| `GET/PUT/DELETE` | `/api/agents/<id>` | 🔒 | Get / update / delete agent |
| `POST` | `/api/tasks` | 🔒 | Submit a task |
| `GET` | `/api/tasks` | 🔒 | List tasks |
| `GET/PUT/DELETE` | `/api/tasks/<id>` | 🔒 | Get / update / delete task |
| `POST` | `/api/workforce/assign` | 🔒 | Assign task to agent |
| `GET` | `/api/workforce/summary` | 🔒 | Workforce statistics |
| `POST` | `/api/ai/complete` | 🔒 | OpenAI chat completion |
| `POST` | `/api/ai/chat` | 🔒 | **Sapphire memory-augmented chat** |
| `POST` | `/api/ai/embed` | 🔒 | Generate embedding vector |
| `POST` | `/api/ai/image` | 🔒 | DALL·E image generation |
| `POST` | `/api/ai/transcribe` | 🔒 | Whisper audio transcription |
| `POST` | `/api/ai/translate` | 🔒 | DeepL translation |
| `POST` | `/api/ai/hf` | 🔒 | HuggingFace inference |
| `POST` | `/api/memory/save` | 🔒 | Save a Sapphire memory |
| `POST` | `/api/memory/search` | 🔒 | Semantic memory search |
| `GET` | `/api/memory/list` | 🔒 | List recent memories |
| `POST` | `/api/memory/reflect` | 🔒 | Trigger memory reflection |
| `DELETE` | `/api/memory/<id>` | 🔒 | Delete a memory entry |
| `POST` | `/api/voice/tts` | 🔒 | ElevenLabs text-to-speech |
| `POST` | `/api/voice/stt` | 🔒 | AssemblyAI speech-to-text |
| `GET` | `/api/voice/voices` | 🔒 | List TTS voices |
| `POST` | `/api/search/vector/upsert` | 🔒 | Pinecone vector upsert |
| `POST` | `/api/search/vector/query` | 🔒 | Pinecone vector query |
| `GET` | `/api/search/web` | 🔒 | SerpAPI web search |
| `POST` | `/api/search/algolia` | 🔒 | Algolia keyword search |
| `POST` | `/api/integrations/webhook` | 🔒 | Relay signed webhook |
| `POST` | `/api/integrations/webhook/verify` | — | Verify inbound webhook |
| `GET/POST` | `/api/integrations/airtable/<table>` | 🔒 | Airtable read/create |
| `POST` | `/api/integrations/sheets/append` | 🔒 | Google Sheets append |
| `GET` | `/api/integrations/services` | — | List configured services |
| `POST/GET` | `/api/leads` | 🔒 | Create / list leads |
| `GET/PUT/DELETE` | `/api/leads/<id>` | 🔒 | Manage lead |
| `POST` | `/api/leads/<id>/score` | 🔒 | AI-score a lead |
| `POST` | `/api/leads/<id>/route` | 🔒 | Route lead to agent |
| `POST` | `/api/leads/<id>/follow-up` | 🔒 | Generate follow-up |
| `POST/GET` | `/api/comms/sms` | 🔒 | Twilio SMS |
| `POST` | `/api/comms/whatsapp` | 🔒 | Twilio WhatsApp |
| `POST` | `/api/comms/call` | 🔒 | Twilio voice call |
| `POST` | `/api/comms/email` | 🔒 | SendGrid email |
| `POST/GET` | `/api/analytics/events` | 🔒 | Track / list events |
| `GET` | `/api/analytics/metrics` | 🔒 | Aggregated metrics |
| `POST/GET` | `/api/analytics/feedback` | 🔒 | Agent feedback |
| `GET` | `/api/audit` | 🔒 | Audit log |
| `POST` | `/api/framework/agents/spawn` | 🔒 | Spawn framework agent |
| `GET` | `/api/framework/agents` | 🔒 | List framework agents |
| `POST` | `/api/framework/run` | 🔒 | Execute a goal |
| `GET` | `/api/framework/status` | 🔒 | Framework status |
| `GET` | `/api/status` | — | System status |
| `GET` | `/api/health` | — | Health check |

---

## Development

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install chromadb sentry-sdk  # optional extras
cp .env.example .env
pytest tests/ -v
```

---

## Documentation

- [Quick Start](docs/QUICKSTART.md)
- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Update Monitor](docs/UPDATE_MONITOR.md)
- [Sapphire Memory System](agents/devonn/memory.md)

---

## License

[MIT](LICENSE) © 2024 DecawDevonn

