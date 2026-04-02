# Quick Start Guide — OpenClaw

**OpenClaw** is an AI Agent Workforce Management System: a Python/Flask REST API
for creating, orchestrating, and coordinating intelligent agents and their tasks,
with built-in JWT authentication, AI/NLP integrations, voice, semantic search,
and the **Sapphire Cognitive Memory** layer.

---

## 1. Fastest Start (Docker)

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw

# Copy and edit the environment template
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and JWT_SECRET

docker compose up -d
curl http://localhost:8080/api/health
# → {"status":"healthy",...}
```

---

## 2. Install via pip

```bash
pip install open-claw

# Start with defaults (in-memory storage)
python -c "from app import create_app; create_app().run(port=8080)"
```

---

## 3. From Source (development)

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw

# Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install core dependencies
pip install -r requirements.txt

# Optional: persistent vector memory (Sapphire Protocol)
pip install chromadb

# Copy environment template
cp .env.example .env

# Start the server
python app.py
# → Listening on http://0.0.0.0:8080
```

---

## 4. First API Calls

### Register a user and get a token

```bash
# Register
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "operator"}'
# → {"id":"...","username":"operator","token":"<JWT>"}

export TOKEN=<JWT>
```

### Create an agent

```bash
curl -X POST http://localhost:8080/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Worker-1","type":"executor","capabilities":["ml","data"]}'
# → {"id":"...","name":"Worker-1","status":"idle",...}
```

### Submit a task

```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Analyse dataset","priority":"high"}'
# → {"id":"...","name":"Analyse dataset","status":"pending",...}
```

### Memory-augmented chat (Sapphire Cognitive Wrapper)

```bash
# Save a memory
curl -X POST http://localhost:8080/api/memory/save \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content":"Wesley Little is the Root Operator.","tags":["identity"]}'

# Chat — memories are automatically retrieved and injected
curl -X POST http://localhost:8080/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"prompt":"Who is the Root Operator?"}' \
  -d '{"prompt":"Who is the Root Operator?","save_response":true}'
```

---

## 5. Run Tests

```bash
pip install pytest pytest-cov chromadb
pytest tests/ -v
```

---

## 6. Key Configuration

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-secret` | Flask session key — **change in production** |
| `JWT_SECRET` | `change-me-jwt` | JWT signing key — **change in production** |
| `OPENAI_API_KEY` | — | Enables AI completion, embedding, image, Whisper |
| `MONGO_URL` | — | Enables persistent MongoDB storage |
| `CHROMA_PERSIST_DIR` | `./chroma_memory` | ChromaDB data directory (Sapphire memory) |

See `.env.example` for the full list (~50 variables).

---

## 7. Documentation

| Doc | Description |
|---|---|
| [API Reference](docs/API.md) | Complete endpoint reference |
| [Architecture](docs/ARCHITECTURE.md) | System design and data flow |
| [Installation Guide](docs/INSTALLATION.md) | All install methods |
| [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) | Hardened production setup |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [Update Monitor](docs/UPDATE_MONITOR.md) | Automated upgrade daemon |
| [Sapphire Memory](agents/devonn/memory.md) | Cognitive memory system design |
