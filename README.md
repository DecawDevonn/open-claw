# OpenClaw

**AI Agent Workforce Management System** — a lightweight REST API for creating, tracking, and coordinating AI agents and their tasks.

[![Build and Test](https://github.com/DecawDevonn/open-claw/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/DecawDevonn/open-claw/actions/workflows/build-and-test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## Quickstart

### Docker (easiest)

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
docker compose up -d
curl http://localhost:8080/api/health
```

### pip

```bash
pip install open-claw
python app.py
```

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/agents` | Create an agent |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/agents/<id>` | Get agent details |
| `PUT` | `/api/agents/<id>` | Update agent |
| `DELETE` | `/api/agents/<id>` | Delete agent |
| `POST` | `/api/tasks` | Submit a task |
| `GET` | `/api/tasks` | List tasks (filter by `status`, `agent_id`) |
| `GET` | `/api/tasks/<id>` | Get task details |
| `PUT` | `/api/tasks/<id>` | Update task status/result |
| `DELETE` | `/api/tasks/<id>` | Delete task |
| `POST` | `/api/workforce/assign` | Assign task to agent |
| `GET` | `/api/workforce/summary` | Workforce statistics |
| `GET` | `/api/status` | System status |
| `GET` | `/api/health` | Health check |

### Example

```bash
# Create an agent
curl -X POST http://localhost:8080/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "Worker-1", "type": "compute", "capabilities": ["ml", "data"]}'

# Submit a task
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name": "Train model", "priority": "high"}'

# Check system status
curl http://localhost:8080/api/status
```

---

## Development

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
python3 -m venv .venv && source .venv/bin/activate
pip install flask pytest pytest-cov
pytest tests/ -v
```

---

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [All Install Methods](docs/INSTALL_METHODS.md)
- [Update Monitor](docs/UPDATE_MONITOR.md)

---

## License

[MIT](LICENSE) © 2024 DecawDevonn

