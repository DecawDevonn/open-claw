# System Architecture

## Overview

OpenClaw is a Python/Flask REST API for managing AI agent workforces. It follows a simple layered architecture optimized for clarity and extensibility.

```
┌─────────────────────────────────────────────┐
│               HTTP Clients                   │
│        (curl, SDK, web dashboard)            │
└─────────────────────┬───────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────┐
│           nginx / Load Balancer              │
│         (TLS termination, routing)           │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│         Flask Application (Gunicorn)         │
│  ┌──────────────────────────────────────┐   │
│  │           create_app()               │   │
│  │  /api/agents   /api/tasks            │   │
│  │  /api/health   /api/status           │   │
│  │  /api/workforce/*                    │   │
│  └──────────────────────────────────────┘   │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│            Storage Layer                     │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │  In-Memory Dict │  │  MongoStorage    │  │
│  │  (development)  │  │  (production)    │  │
│  └─────────────────┘  └──────────────────┘  │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│              MongoDB 6                       │
│   Collections: agents, tasks, users,         │
│                revoked_tokens                │
└─────────────────────────────────────────────┘
```

---

## Components

### Flask Application (`app.py`)

Uses the **application factory pattern** (`create_app()`), which:

- Enables clean test isolation (each test gets a fresh app instance)
- Avoids circular imports
- Supports multiple configurations (testing, production)

### API Endpoints

| Group | Endpoints |
|---|---|
| Agents | `POST/GET /api/agents`, `GET/PUT/DELETE /api/agents/<id>` |
| Tasks | `POST/GET /api/tasks`, `GET/PUT/DELETE /api/tasks/<id>` |
| Workforce | `POST /api/workforce/assign`, `GET /api/workforce/summary` |
| System | `GET /api/health`, `GET /api/status` |

### Storage Layer (`storage/`)

- **In-memory** (`_agents`, `_tasks` dicts in `app.py`): Used by default; fast, zero-dependency, reset on restart.
- **MongoStorage** (`storage/mongo.py`): Drop-in persistent backend backed by MongoDB. Implements the same interface so the application layer is storage-agnostic.

### Data Flow

```
Client → nginx → Gunicorn (workers) → Flask route handler
                                           │
                                     Validate input
                                           │
                                   Read/write storage
                                           │
                                    Return JSON response
```

---

## Security Model

- **Non-root container**: The Docker image runs as user `openclaw` (no shell)
- **TLS**: Enforced at the nginx layer; the app itself speaks plain HTTP internally
- **Secrets**: Passed via environment variables, never hardcoded
- **Error messages**: Generic messages returned to clients; details logged server-side only
- **Health check**: `/api/health` is unauthenticated and returns minimal info

---

## Scalability

OpenClaw scales horizontally:

1. Run multiple Gunicorn instances behind a load balancer
2. All instances share a single MongoDB cluster (replica set recommended)
3. MongoDB handles concurrent writes with document-level locking

For extreme scale, the in-memory storage can be swapped for Redis with minimal code changes.

---

## Directory Structure

```
open-claw/
├── app.py                  # Flask application factory
├── openclaw/               # Python package metadata
│   └── __init__.py
├── storage/                # Storage backends
│   ├── base.py             # Abstract base class
│   └── mongo.py            # MongoDB backend
├── tests/                  # Test suite
│   └── test_api.py
├── docs/                   # Documentation
├── scripts/                # Utility shell scripts
├── .github/workflows/      # CI/CD pipelines
├── Dockerfile              # Multi-stage container build
├── docker-compose.yml      # Local/production compose stack
├── requirements.txt        # Python dependencies
└── pyproject.toml          # Build configuration
```
