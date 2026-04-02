# OpenClaw API Reference

**Base URL:** `http://localhost:8080` (or your deployed host)

**Authentication:** Most endpoints require a Bearer JWT in the `Authorization` header.
Obtain a token via `POST /api/auth/register` or `POST /api/auth/token`.

Public endpoints (no auth required): `/api/health`, `/api/status`,
`/api/integrations/services`, `/api/integrations/webhook/verify`.

---

## System

### `GET /api/health`
Returns application health, uptime, and configured integrations.

**Response `200`**
```json
{"status":"healthy","uptime_seconds":42,"integrations":{"configured":["openai","twilio"]}}
```

### `GET /api/status`
Returns counts of active agents and tasks.

**Response `200`**
```json
{"status":"running","agents":{"total":3,"idle":2,"running":1},"tasks":{"total":10,"completed":7,"pending":2}}
```

---

## Authentication — `/api/auth/*`

### `POST /api/auth/register`
Register a new user and receive a JWT.

**Body**
```json
{"username": "operator"}
```

**Response `201`**
```json
{"id":"uuid","username":"operator","token":"<JWT>","expires_in":86400}
```

### `POST /api/auth/token`
Exchange credentials for a JWT.

**Body**
```json
{"username": "operator"}
```

**Response `200`**
```json
{"token":"<JWT>","expires_in":86400}
```

### `GET /api/auth/me` 🔒
Return the currently authenticated user.

**Response `200`**
```json
{"id":"uuid","username":"operator","created_at":"2024-01-01T00:00:00Z"}
```

### `POST /api/auth/revoke` 🔒
Revoke the current JWT (adds JTI to revocation list).

**Response `200`**
```json
{"status":"revoked"}
```

---

## Agents — `/api/agents`

### `POST /api/agents` 🔒
Create a new agent.

**Body**
```json
{"name":"Worker-1","type":"executor","capabilities":["ml","data"],"metadata":{}}
```

**Response `201`**
```json
{"id":"uuid","name":"Worker-1","type":"executor","status":"idle","capabilities":["ml","data"],"created_at":"..."}
```

### `GET /api/agents` 🔒
List all agents.

**Response `200`** — array of agent objects.

### `GET /api/agents/<id>` 🔒
Get a single agent by ID. Returns `404` if not found.

### `PUT /api/agents/<id>` 🔒
Update agent fields (partial update).

### `DELETE /api/agents/<id>` 🔒
Delete an agent. Returns `404` if not found.

---

## Tasks — `/api/tasks`

### `POST /api/tasks` 🔒
Submit a new task.

**Body**
```json
{"name":"Analyse dataset","description":"Run PCA on feature matrix","priority":"high","agent_id":"uuid"}
```

**Response `201`**
```json
{"id":"uuid","name":"Analyse dataset","status":"pending","priority":"high","created_at":"..."}
```

### `GET /api/tasks` 🔒
List tasks. Optional query params: `?status=pending`, `?agent_id=<id>`.

### `GET /api/tasks/<id>` 🔒
Get a single task. Returns `404` if not found.

### `PUT /api/tasks/<id>` 🔒
Update task status or result.

**Body**
```json
{"status":"completed","result":"PCA complete — 3 components explain 92% variance"}
```

### `DELETE /api/tasks/<id>` 🔒
Delete a task.

---

## Workforce — `/api/workforce`

### `POST /api/workforce/assign` 🔒
Assign a task to an agent.

**Body**
```json
{"task_id":"uuid","agent_id":"uuid"}
```

**Response `200`**
```json
{"status":"assigned","task_id":"uuid","agent_id":"uuid"}
```

### `GET /api/workforce/summary` 🔒
Return workforce statistics.

**Response `200`**
```json
{"agents_count":5,"tasks_count":12,"completed":8,"pending":3,"running":1}
```

---

## AI / NLP — `/api/ai/*` 🔒

### `POST /api/ai/complete`
OpenAI chat completion.

**Body**
```json
{"prompt":"Summarise the last quarter","system":"You are a data analyst.","model":"gpt-4o-mini","max_tokens":512,"temperature":0.7}
```

**Response `200`**
```json
{"result":"..."}
```

### `POST /api/ai/chat`
**Sapphire Cognitive Wrapper** — memory-augmented chat.
Retrieves relevant memories from ChromaDB, injects them as context, calls the LLM,
and optionally saves the response back to memory.

**Body**
```json
{
  "prompt": "What do you remember about the project?",
  "system": "You are DEVONN.AI.",
  "model": "gpt-4o-mini",
  "max_tokens": 1024,
  "temperature": 0.7,
  "save_response": true,
  "memory_format": "Q: {prompt}\nA: {reply}"
}
```

**Response `200`**
```json
{"result":"...","memories_used":[{"id":"...","content":"...","relevance":0.92}],"memory_saved_id":"uuid"}
```

### `POST /api/ai/embed`
Generate an embedding vector.

**Body**
```json
{"text":"Agent orchestration platform","model":"text-embedding-3-small"}
```

**Response `200`**
```json
{"embedding":[0.01,-0.03,...],"dimensions":1536}
```

### `POST /api/ai/image`
Generate images via DALL·E 3.

**Body**
```json
{"prompt":"A futuristic AI control room","size":"1024x1024","n":1}
```

**Response `200`**
```json
{"images":["https://oai.dall-e.example/..."]}
```

### `POST /api/ai/transcribe`
Transcribe audio via Whisper. Send `multipart/form-data` with an `audio` file field.

**Response `200`**
```json
{"text":"Hello, this is a test transcription."}
```

### `POST /api/ai/translate`
Translate text via DeepL.

**Body**
```json
{"text":"Bonjour le monde","target_lang":"EN-US"}
```

**Response `200`**
```json
{"result":"Hello world","source_lang":"FR"}
```

### `POST /api/ai/hf`
Run inference against a HuggingFace model.

**Body**
```json
{"text":"Classify this review: I loved it!","model":"distilbert-base-uncased-finetuned-sst-2-english"}
```

**Response `200`**
```json
{"result":[{"label":"POSITIVE","score":0.9998}]}
```

---

## Sapphire Memory — `/api/memory/*` 🔒

The Sapphire Protocol gives DEVONN.AI persistent vector memory backed by ChromaDB.
See [agents/devonn/memory.md](../agents/devonn/memory.md) for the full design.

### `POST /api/memory/save`
Persist a memory entry.

**Body**
```json
{"content":"Wesley Little is the Root Operator.","weight":1.5,"tags":["identity"],"type":"memory"}
```

**Response `201`**
```json
{"id":"uuid","status":"saved"}
```

### `POST /api/memory/search`
Semantic nearest-neighbour search.

**Body**
```json
{"query":"Who built OpenClaw?","n":5}
```

**Response `200`**
```json
{"results":[{"id":"uuid","content":"...","relevance":0.94,"tags":["identity"]}],"count":1}
```

### `GET /api/memory/list`
List most-recent memories.

**Query params:** `?limit=50` (default)

**Response `200`**
```json
{"memories":[...],"count":12,"total":12}
```

### `POST /api/memory/reflect`
Trigger a Sapphire reflection — summarises the most-recent N memories into a single
insight and saves it back to the store.

**Body**
```json
{"n":5}
```

**Response `201`**
```json
{"status":"reflected","memory_id":"uuid"}
```

Returns `200 {"status":"skipped"}` when there are fewer than 2 memories or no AI key.

### `DELETE /api/memory/<id>`
Delete a memory entry.

**Response `200`**
```json
{"status":"deleted","id":"uuid"}
```

Returns `404` if the entry does not exist.

---

## Voice — `/api/voice/*` 🔒

### `POST /api/voice/tts`
Convert text to speech via ElevenLabs. Returns base64-encoded MP3.

**Body**
```json
{"text":"Hello, I am DEVONN.AI.","voice_id":"EXAVITQu4vr4xnSDxMaL","stability":0.5,"similarity_boost":0.75}
```

**Response `200`**
```json
{"audio_base64":"<base64>","content_type":"audio/mpeg"}
```

### `POST /api/voice/stt`
Transcribe audio via AssemblyAI. Send `multipart/form-data` or JSON `{"audio_url":"..."}`.

**Response `200`**
```json
{"text":"...","words":[{"text":"Hello","start":0,"end":400}]}
```

### `GET /api/voice/voices`
List available ElevenLabs voices.

**Response `200`**
```json
{"voices":[{"voice_id":"...","name":"Rachel"}]}
```

---

## Search — `/api/search/*` 🔒

### `POST /api/search/vector/upsert`
Upsert vectors into Pinecone.

**Body**
```json
{"id":"doc-1","vector":[0.1,0.2,...],"metadata":{"source":"manual"}}
```

**Response `200`**
```json
{"status":"upserted"}
```

### `POST /api/search/vector/query`
Query Pinecone for nearest neighbours.

**Body**
```json
{"vector":[0.1,0.2,...],"top_k":5}
```

**Response `200`**
```json
{"matches":[{"id":"doc-1","score":0.98,"metadata":{}}]}
```

### `GET /api/search/web`
Google search via SerpAPI.

**Query params:** `?q=OpenClaw+agent+system&num=5`

**Response `200`**
```json
{"results":[{"title":"...","link":"...","snippet":"..."}]}
```

### `POST /api/search/algolia`
Keyword search via Algolia.

**Body**
```json
{"index":"products","query":"agent","filters":"type:executor"}
```

**Response `200`**
```json
{"hits":[...],"nbHits":3}
```

---

## Integrations — `/api/integrations/*`

### `POST /api/integrations/webhook` 🔒
Relay a signed webhook payload to a target URL.

**Body**
```json
{"url":"https://hook.example.com/endpoint","payload":{"event":"task.complete"}}
```

**Response `200`**
```json
{"status":"delivered","target_status":200}
```

### `POST /api/integrations/webhook/verify`
Verify an inbound webhook signature (public endpoint).

**Body**
```json
{"payload":"...","signature":"sha256=..."}
```

**Response `200`**
```json
{"valid":true}
```

### `GET /api/integrations/airtable/<table>` 🔒
List records from an Airtable table.

### `POST /api/integrations/airtable/<table>` 🔒
Create a record in an Airtable table.

**Body**
```json
{"fields":{"Name":"New lead","Status":"Open"}}
```

### `POST /api/integrations/sheets/append` 🔒
Append a row to a Google Sheet.

**Body**
```json
{"spreadsheet_id":"1BxiMVs...","range":"Sheet1!A1","values":[["Alice","Engineering"]]}
```

### `GET /api/integrations/services`
List configured integration services (public endpoint — no auth required).

**Response `200`**
```json
{"configured":["openai","twilio","sentry"]}
```

---

## Leads — `/api/leads/*` 🔒

### `POST /api/leads`
Create a new lead.

**Body**
```json
{"name":"Acme Corp","email":"ceo@acme.com","source":"website","metadata":{}}
```

**Response `201`** — lead object with `id`.

### `GET /api/leads`
List all leads.

### `GET /api/leads/<id>`
Get a lead by ID.

### `PUT /api/leads/<id>`
Update lead fields.

### `POST /api/leads/<id>/score`
AI-score a lead.

**Response `200`**
```json
{"lead_id":"uuid","score":0.87,"rationale":"High engagement signals"}
```

### `POST /api/leads/<id>/route`
Route a lead to the best-fit agent.

### `POST /api/leads/<id>/follow-up`
Generate and schedule a follow-up action.

### `DELETE /api/leads/<id>`
Delete a lead.

---

## Communications — `/api/comms/*` 🔒

### `POST /api/comms/sms`
Send an SMS via Twilio.

**Body**
```json
{"to":"+1555XXXXXXX","message":"Your task is complete."}
```

### `POST /api/comms/whatsapp`
Send a WhatsApp message via Twilio.

**Body**
```json
{"to":"+1555XXXXXXX","message":"Agent update: task finished."}
```

### `POST /api/comms/call`
Place a phone call via Twilio.

**Body**
```json
{"to":"+1555XXXXXXX","twiml":"<Response><Say>Task complete.</Say></Response>"}
```

### `POST /api/comms/email`
Send an email via SendGrid.

**Body**
```json
{"to":"operator@example.com","subject":"Task complete","body":"All steps finished."}
```

---

## Analytics — `/api/analytics/*` 🔒

### `POST /api/analytics/events`
Track a custom event.

**Body**
```json
{"event_type":"task.complete","agent_id":"uuid","metadata":{"duration_ms":1200}}
```

### `GET /api/analytics/metrics`
Return aggregated event metrics. Optional: `?since=2024-01-01T00:00:00Z`.

### `POST /api/analytics/feedback`
Submit agent feedback.

**Body**
```json
{"agent_id":"uuid","rating":5,"comment":"Excellent response quality"}
```

### `GET /api/analytics/feedback`
List feedback entries. Optional: `?agent_id=<id>`.

---

## Audit — `/api/audit` 🔒

### `GET /api/audit`
Return the most-recent audit log entries (every authenticated request is logged).

**Query params:** `?limit=200`

**Response `200`**
```json
{"entries":[{"method":"POST","path":"/api/tasks","status":201,"actor_id":"uuid","ts":"..."}],"count":50}
```

---

## Framework — `/api/framework/*` 🔒

### `POST /api/framework/agents/spawn`
Spawn a framework agent from a declarative config.

**Body**
```json
{"name":"research-agent","role":"executor","model":"gpt-4o","tools":["save_to_memory"],"max_steps":10}
```

**Response `201`** — spawned agent object.

### `GET /api/framework/agents`
List all spawned framework agents.

### `GET /api/framework/agents/<id>`
Get a framework agent by ID.

### `POST /api/framework/run`
Run a goal through the framework executor (TaskExecutor + MetaPlanner + ToolRegistry).

**Body**
```json
{"goal":"Research and summarise the latest AI news","strategy":"sequential","agent":{"name":"researcher","role":"analyst"}}
```

**Response `200`**
```json
{"agent_id":"uuid","goal":"...","steps_completed":3,"output":"...","status":"done"}
```

### `GET /api/framework/status`
Return framework status and list of active agents.

---

## Error Responses

All error responses share a consistent shape:

```json
{"error": "human-readable description"}
```

| Status | Meaning |
|---|---|
| `400` | Bad request — missing or invalid input |
| `401` | Unauthorized — missing or invalid Bearer token |
| `404` | Not found |
| `503` | Service unavailable — API key not configured |
| `500` | Internal server error |
