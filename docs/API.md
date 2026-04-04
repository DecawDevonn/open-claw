# API Documentation

## Overview

open-claw exposes a versioned REST API at `/api/v1/`. All protected endpoints require a JWT access token in the `Authorization: Bearer <token>` header.

## Base URL

```
http://localhost:8080
```

## Authentication

### POST `/api/v1/auth/register`
Register a new user. Rate-limited to **10 per minute**.

**Body**
```json
{ "username": "alice", "password": "s3cur3p4ss", "role": "user" }
```
`role` defaults to `"user"`. Pass `"admin"` for admin privileges.

**Response 201**
```json
{ "message": "User registered successfully", "user_id": "uuid", "username": "alice" }
```

---

### POST `/api/v1/auth/login`
Authenticate and receive JWT tokens. Rate-limited to **10 per minute**.

**Body**
```json
{ "username": "alice", "password": "s3cur3p4ss" }
```

**Response 200**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user_id": "uuid",
  "username": "alice",
  "role": "user"
}
```

---

### POST `/api/v1/auth/refresh`
Exchange a refresh token for a new access token. Send the **refresh** token in the Authorization header.

**Response 200**
```json
{ "access_token": "eyJ..." }
```

---

### POST `/api/v1/auth/logout`
Revoke the current access token. Rate-limited to **30 per minute**. Requires auth.

**Response 200**
```json
{ "message": "Successfully logged out" }
```

---

## Agents

All agent endpoints require authentication.

### POST `/api/v1/agents`
Create an agent.

**Body**
```json
{ "name": "Worker-1", "type": "worker", "capabilities": ["ml", "compute"] }
```
`type` defaults to `"generic"`. `capabilities` defaults to `[]`.

**Response 201** — agent object with `id`, `status: "idle"`, `tasks_completed: 0`, `last_seen_at: null`.

---

### GET `/api/v1/agents`
List agents with pagination and optional filters.

**Query params:** `page` (default 1), `per_page` (default 20, max 100), `status`, `sort_by`, `sort_order`

**Response 200**
```json
{ "items": [...], "total": 5, "page": 1, "per_page": 20, "pages": 1 }
```

---

### GET `/api/v1/agents/<agent_id>`
Get a single agent. **404** if not found.

---

### PUT `/api/v1/agents/<agent_id>`
Update `status`, `name`, or `capabilities`. Valid statuses: `idle`, `busy`, `offline`, `error`.

---

### DELETE `/api/v1/agents/<agent_id>`
Delete an agent. **Response 200** `{ "message": "Agent deleted successfully" }`.

---

### POST `/api/v1/agents/<agent_id>/heartbeat`
Update `last_seen_at` to now. Revives `offline` agents to `idle`.

**Response 200** — updated agent object.

---

## Tasks

All task endpoints require authentication.

### POST `/api/v1/tasks`
Submit a task.

**Body**
```json
{ "name": "Train model", "description": "...", "priority": "high", "agent_id": "uuid" }
```
Valid priorities: `low`, `normal` (default), `high`, `critical`. `agent_id` is optional.

**Response 201** — task object with `status: "pending"`.

---

### GET `/api/v1/tasks`
List tasks. **Query params:** `page`, `per_page`, `status`, `agent_id`, `sort_by`, `sort_order`.

---

### GET `/api/v1/tasks/<task_id>`
Get a single task.

---

### PUT `/api/v1/tasks/<task_id>`
Update `status` or `result`. Valid statuses: `pending`, `assigned`, `running`, `completed`, `failed`, `cancelled`.
Setting `running` auto-sets `started_at`; terminal statuses auto-set `completed_at`.

---

### DELETE `/api/v1/tasks/<task_id>`
Delete a task.

---

## Workforce

### POST `/api/v1/workforce/assign`
Assign a task to an agent. Sets task status to `assigned` and agent status to `busy`.

**Body**
```json
{ "task_id": "uuid", "agent_id": "uuid" }
```

**Response 200**
```json
{ "task": { ... }, "agent": { ... } }
```

---

### GET `/api/v1/workforce/summary`
Capability map, counts, and full agent/task lists.

**Response 200**
```json
{
  "agents_count": 3,
  "tasks_count": 7,
  "capabilities": { "ml": 2, "compute": 1 },
  "agents": [...],
  "tasks": [...]
}
```

---

## Health & Status

These endpoints are public (no auth required).

### GET `/api/health` · GET `/api/v1/health`
```json
{ "status": "healthy", "timestamp": "2024-01-01T00:00:00Z", "version": "1.0.0" }
```

### GET `/api/status` · GET `/api/v1/status`
```json
{
  "status": "running",
  "timestamp": "...",
  "version": "1.0.0",
  "agents": { "total": 3, "idle": 2, "active": 1 },
  "tasks": { "total": 7, "running": 1, "completed": 4, "pending": 2 }
}
```

---

## Error Responses

All errors return JSON:

```json
{ "error": "Human-readable message", "code": "MACHINE_READABLE_CODE" }
```

| HTTP | Code |
|---|---|
| 400 | `INVALID_INPUT`, `MISSING_FIELDS` |
| 401 | `UNAUTHORIZED`, `TOKEN_EXPIRED`, `TOKEN_REVOKED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 422 | `INVALID_TOKEN` |
| 500 | `INTERNAL_ERROR` |
