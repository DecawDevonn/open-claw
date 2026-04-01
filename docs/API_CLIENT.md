# API Client Documentation

## Overview

`openclaw_client.OpenClawClient` is a synchronous Python HTTP client for the
OpenClaw REST API. It includes retry logic, optional request logging, and
typed return values.

## Quick Start

```python
from openclaw_client import OpenClawClient

client = OpenClawClient(profile='dev')
health = client.get_health()
print(health)  # {'status': 'healthy', ...}
```

## Constructor

```python
OpenClawClient(
    config=None,        # Optional OpenClawConfig instance
    profile=None,       # Profile name: 'dev' | 'staging' | 'prod'
    log_requests=False, # Log every request/response at DEBUG level
)
```

---

## Methods

### Health

#### `get_health() → dict`

Check API health.

```python
result = client.get_health()
# {'status': 'healthy', 'timestamp': '...', 'uptime': 'running'}
```

---

### Agents

#### `list_agents() → list[dict]`

Return all agents.

#### `get_agent(agent_id: str) → dict`

Return details for a single agent.

#### `create_agent(name, agent_type='generic', capabilities=None) → dict`

Create a new agent.

```python
agent = client.create_agent("worker-1", capabilities=["compute", "ml"])
```

#### `update_agent(agent_id, **fields) → dict`

Update agent fields (`status`, `capabilities`, …).

#### `delete_agent(agent_id) → dict`

Delete an agent.

---

### Tasks

#### `get_tasks(status=None, agent_id=None) → list[dict]`

Return tasks, optionally filtered.

#### `get_task(task_id) → dict`

Return a single task.

#### `create_task(name, description='', agent_id=None, priority='normal') → dict`

Submit a new task.

```python
task = client.create_task(
    "Deploy service",
    description="Deploy auth service",
    agent_id=agent['id'],
    priority='high',
)
```

#### `update_task(task_id, **fields) → dict`

Update task fields.

```python
client.update_task(task['id'], status='running')
client.update_task(task['id'], status='completed', result={"output": "done"})
```

#### `delete_task(task_id) → dict`

Delete a task.

---

### Fortress

#### `execute_command(agent_id, command, auto_approve=True) → dict`

Execute a shell command on an agent via the Fortress engine.

```python
result = client.execute_command("agent-1", "ls -la", auto_approve=True)
```

#### `query_facts(agent=None, tag=None) → list[dict]`

Query the Fortress fact graph.

```python
facts = client.query_facts(agent="agent-1", tag="critical")
```

#### `get_fortress_stats() → dict`

Return Fortress engine statistics.

---

### Workforce

#### `assign_task(task_id, agent_id) → dict`

Assign a task to an agent.

#### `get_status() → dict`

Return overall system status (agents, tasks counts).

---

## Error Handling

All methods raise `OpenClawError` on failure.

```python
from openclaw_client import OpenClawClient, OpenClawError

client = OpenClawClient()
try:
    agent = client.get_agent("nonexistent-id")
except OpenClawError as e:
    print(e)            # Human-readable message
    print(e.status_code)  # HTTP status code (or None for network errors)
    print(e.response)     # Raw response body
```

### Error Codes

| Status | Meaning |
|--------|---------|
| `400` | Bad request / validation error |
| `401` | Missing or invalid API key |
| `404` | Resource not found |
| `429` | Rate limited (auto-retried) |
| `500` | Internal server error (auto-retried up to 3 times) |
| `None` | Network/connection error |

---

## Configuration

The client reads configuration through `OpenClawConfig` (see `config.py`).
Profile defaults:

| Profile | Base URL | SSL | Timeout |
|---------|----------|-----|---------|
| `dev` | `http://localhost:8080` | No | 30 s |
| `staging` | `https://staging.openclaw.example.com` | Yes | 60 s |
| `prod` | `https://api.openclaw.example.com` | Yes | 60 s |

Override with environment variables:

```bash
OPENCLAW_BASE_URL=http://myserver:8080
OPENCLAW_API_KEY=secret-token
OPENCLAW_TIMEOUT=60
```
