# Quick Start Guide — OpenClaw

Get up and running in 5 minutes.

## 1. Prerequisites

- Python 3.8+
- pip

## 2. Clone & Install

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw

# Install in editable mode (includes CLI entry point)
pip install -e .
# or just install dependencies
pip install -r requirements.txt
```

## 3. Configure

Copy the example env file and edit as needed:

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY
```

Optional: Create a profile config:

```bash
mkdir -p ~/.openclaw
cat > ~/.openclaw/config.json << 'EOF'
{
  "dev": {
    "base_url": "http://localhost:8080"
  }
}
EOF
```

## 4. Start the Server

```bash
python app.py
# API is now at http://localhost:8080
```

## 5. Your First Command

```bash
# Check health
python cli.py status

# Create an agent
python cli.py agents create my-first-agent

# List agents
python cli.py agents list

# Submit a task
python cli.py tasks create "Hello World" --description "My first task"

# List tasks
python cli.py tasks list
```

## 6. Run an Example Workflow

```bash
python examples/simple_agent.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Address already in use` | Kill the process on port 8080: `lsof -ti:8080 \| xargs kill` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Connection refused` | Start the server: `python app.py` |
| `openclaw: command not found` | Run `pip install -e .` |

## Next Steps

- [CLI User Guide](CLI_GUIDE.md) — Full command reference
- [API Client Docs](API_CLIENT.md) — Python client reference
- [Examples](EXAMPLES.md) — Working example scripts
