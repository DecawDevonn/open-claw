# CLI User Guide

## Overview

`openclaw` is the command-line interface for the OpenClaw agent orchestration platform.

## Installation

```bash
pip install -e .
# or run directly:
python cli.py --help
```

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Config profile: `dev` (default), `staging`, `prod` |
| `--output` | `-o` | Output format: `table` (default), `json`, `yaml` |
| `--verbose` | `-v` | Enable request/response logging |

## Commands

### `openclaw config`

Display the current configuration for the active profile.

```bash
openclaw config
openclaw --profile prod config
openclaw --output json config
```

---

### `openclaw status`

Check API health and system status.

```bash
openclaw status
openclaw --profile staging status
```

---

### `openclaw agents`

Manage agents.

#### List agents

```bash
openclaw agents list
openclaw --output json agents list
```

#### Create an agent

```bash
openclaw agents create my-agent
openclaw agents create worker --type compute --capabilities data --capabilities ml
```

#### Delete an agent

```bash
openclaw agents delete <agent-id>
```

---

### `openclaw tasks`

Manage tasks.

#### List tasks

```bash
openclaw tasks list
openclaw tasks list --status completed
openclaw tasks list --agent <agent-id>
```

#### Create a task

```bash
openclaw tasks create "My Task"
openclaw tasks create "Deploy" --description "Deploy service X" --agent <agent-id> --priority high
```

---

### `openclaw execute`

Execute a command on a specific agent via the Fortress engine.

```bash
openclaw execute <agent-id> "ls -la"
openclaw execute <agent-id> "git status" --no-approve
```

---

### `openclaw facts`

Query the Fortress knowledge / fact graph.

```bash
openclaw facts
openclaw facts --agent <agent-id>
openclaw facts --tag critical
openclaw --output json facts
```

---

### `openclaw logs`

View agent activity logs.

```bash
openclaw logs
openclaw logs <agent-id> --tail 100
```

---

### `openclaw deploy`

Deploy a workflow or service configuration.

```bash
openclaw deploy
openclaw deploy my-workflow
openclaw deploy my-workflow --dry-run
```

---

## Configuration

OpenClaw reads configuration in the following priority order:

1. Environment variables (`OPENCLAW_BASE_URL`, `OPENCLAW_API_KEY`, …)
2. `~/.openclaw/config.json` (keyed by profile name)
3. Built-in profile defaults

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCLAW_BASE_URL` | API base URL | `http://localhost:8080` |
| `OPENCLAW_API_KEY` | Bearer token | _(none)_ |
| `OPENCLAW_TIMEOUT` | Request timeout (seconds) | `30` |
| `OPENCLAW_VERIFY_SSL` | Verify TLS certificates | `false` |
| `OPENCLAW_PROFILE` | Active profile | `dev` |

### Config File Example (`~/.openclaw/config.json`)

```json
{
  "dev": {
    "base_url": "http://localhost:8080",
    "timeout": 30
  },
  "prod": {
    "base_url": "https://api.openclaw.example.com",
    "api_key": "your-token-here",
    "verify_ssl": true,
    "timeout": 60
  }
}
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection failed` | Ensure the API server is running: `python app.py` |
| `401 Unauthorized` | Set `OPENCLAW_API_KEY` or configure `api_key` in config file |
| `SSL verification failed` | Set `OPENCLAW_VERIFY_SSL=false` for self-signed certs |
| `Command not found: openclaw` | Run `pip install -e .` or use `python cli.py` |
