# open-claw

**open-claw** is a production-ready Flask API for managing AI agent workforces — create agents, submit tasks, assign work, and track progress, all secured with JWT authentication.

## Features

- **JWT Authentication** — register, login, refresh tokens, and logout with token revocation
- **Agent Management** — full CRUD plus live heartbeat to track agent health
- **Task Management** — submit, assign, and track tasks with priorities and statuses
- **Workforce Orchestration** — assign tasks to agents, view workforce summaries
- **Pluggable Storage** — in-memory (default) or MongoDB via `MONGODB_URI`
- **Rate Limiting** — per-endpoint limits via flask-limiter (Redis or in-memory)
- **CORS** — configurable allowed origins
- **Structured JSON Logging** — every request logged with latency
- **Pagination** — all list endpoints support `page` / `per_page`
- **Gunicorn** — production WSGI entrypoint built in

---

## Quick start (Python)

```bash
git clone https://github.com/your-org/open-claw.git
cd open-claw
pip install -r requirements.txt
python app.py          # uses in-memory storage — no DB needed
```

The API is available at `http://localhost:8080`.

---

## Docker quick start (with MongoDB)

```bash
cp .env.example .env   # edit SECRET_KEY and JWT_SECRET_KEY
docker compose up -d
```

To initialise MongoDB indexes after first boot:

```bash
docker compose exec web python db_init.py
```

---

## Authentication examples

### Register

```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "s3cur3p4ss"}'
```

### Login

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "s3cur3p4ss"}'
# → { "access_token": "...", "refresh_token": "..." }
```

Use `access_token` in subsequent requests:

```bash
export TOKEN=<access_token>
curl http://localhost:8080/api/v1/agents -H "Authorization: Bearer $TOKEN"
```

### Logout (revoke token)

```bash
curl -X POST http://localhost:8080/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

---

## Heartbeat example

Agents should POST to the heartbeat endpoint periodically to remain `idle`. If no heartbeat is received within `AGENT_HEARTBEAT_TIMEOUT` seconds the agent is automatically set to `offline`.

```bash
curl -X POST http://localhost:8080/api/v1/agents/<agent_id>/heartbeat \
  -H "Authorization: Bearer $TOKEN"
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key |
| `JWT_SECRET_KEY` | `jwt-secret-change-in-production` | JWT signing key |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Listen port |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MONGODB_URI` | _(unset — in-memory)_ | MongoDB connection URI |
| `REDIS_URL` | `memory://` | Redis URI for rate-limiter storage |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `AGENT_HEARTBEAT_TIMEOUT` | `60` | Seconds before agent is marked offline |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `FLASK_ENV` | `production` | Flask environment |

---

## Development

```bash
# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
flake8 app.py storage/ --max-line-length=120
```

