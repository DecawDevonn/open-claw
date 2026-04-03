# OpenClaw — AI Agent Workforce System

[![CI](https://github.com/DecawDevonn/open-claw/actions/workflows/ci.yml/badge.svg)](https://github.com/DecawDevonn/open-claw/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

OpenClaw is a production-ready **AI agent workforce orchestration API** built with Flask. It provides a RESTful interface for creating, managing, and coordinating AI agents and their tasks — designed to integrate with dashboards like [Devon AI War Room](https://devonnaiwarroom.lovable.app).

---

## Features

- **Agent Management** — Create, update, list, and delete AI agents with capability tracking
- **Task Orchestration** — Submit, assign, track, and complete tasks across your agent workforce
- **Workforce Dashboard** — Real-time summary of agent availability and task throughput
- **Health & Status** — Built-in `/api/health` and `/api/status` endpoints for monitoring
- **Pluggable Storage** — In-memory (default) or MongoDB backend via `StorageBackend` abstraction
- **Docker Ready** — Full `Dockerfile` and `docker-compose.yml` for one-command deployment
- **CI/CD** — GitHub Actions workflow with linting, type checking, and test coverage

---

## Quick Start

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run the server
python app.py
# API available at http://localhost:8080
```

### Docker

```bash
docker-compose up --build
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agents` | Create a new agent |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/agents/<id>` | Get agent details |
| `PUT` | `/api/agents/<id>` | Update agent |
| `DELETE` | `/api/agents/<id>` | Delete agent |
| `POST` | `/api/tasks` | Submit a new task |
| `GET` | `/api/tasks` | List tasks (filterable) |
| `GET` | `/api/tasks/<id>` | Get task details |
| `PUT` | `/api/tasks/<id>` | Update task status/result |
| `DELETE` | `/api/tasks/<id>` | Delete task |
| `POST` | `/api/workforce/assign` | Assign task to agent |
| `GET` | `/api/workforce/summary` | Workforce statistics |
| `GET` | `/api/status` | System status |
| `GET` | `/api/health` | Health check |

See [docs/API.md](docs/API.md) for full request/response schemas.

---

## Project Structure

```
open-claw/
├── app.py                  # Flask application & all API routes
├── storage/
│   ├── __init__.py         # Package exports
│   ├── base.py             # Abstract StorageBackend interface
│   ├── memory.py           # In-memory backend (default)
│   └── mongo.py            # MongoDB backend
├── tests/
│   └── test_api.py         # API test suite
├── docs/
│   ├── API.md              # Full API documentation
│   ├── ARCHITECTURE.md     # System design
│   ├── DEPLOYMENT.md       # Deployment guide
│   └── QUICKSTART.md       # Getting started guide
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI pipeline
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT © DecawDevonn
