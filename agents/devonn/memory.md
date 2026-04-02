# 🧠 DEVONN.AI — SAPPHIRE MEMORY STRUCTURE

## Overview

The Sapphire Protocol uses a **local ChromaDB vector store** as DEVONN.AI's
persistent memory spine.  Every conversation, insight, and reflection is
embedded and saved so that the agent maintains continuity across sessions.

---

## Storage Backend

| Property | Value |
|---|---|
| Engine | ChromaDB (local persistent store) |
| Embedding model | `text-embedding-3-small` (OpenAI) |
| Distance metric | Cosine similarity |
| Default collection | `sapphire` |
| Persist directory | `./chroma_memory` (configurable via `CHROMA_PERSIST_DIR`) |

---

## Memory Entry Schema

Every memory stored in the vector DB has the following structure:

| Field | Type | Description |
|---|---|---|
| `id` | `string` (UUID) | Unique memory identifier |
| `content` | `string` | The memory text (self-contained statement or Q/A pair) |
| `weight` | `float` 0.0–2.0 | Importance score (default `1.0`; reflections use `1.5`) |
| `tags` | `string[]` | Categorisation labels (e.g. `["conversation", "reflection"]`) |
| `associations` | `string[]` | IDs of related memories |
| `ts` | `float` (Unix epoch) | Creation timestamp |
| `type` | `string` | Entry type: `memory` \| `reflection` |

---

## Retrieval (Injection) Protocol

Before every LLM call via `/api/ai/chat` the Cognitive Wrapper:

1. Embeds the incoming prompt.
2. Queries ChromaDB for the top-K nearest-neighbour memories (default K=5).
3. Injects the results as a `[SAPPHIRE MEMORY — retrieved context]` block
   prepended to the system prompt.
4. Saves the assistant's reply back to memory (tagged `conversation`).

This ensures every response is grounded in accumulated experience.

---

## Self-Reflection Loop

Every **10 saves** (configurable via `SAPPHIRE_REFLECTION_INTERVAL`) the system
automatically:

1. Retrieves the 5 most-recent memory entries.
2. Asks the LLM to summarise them into a single concise insight.
3. Saves the summary as a `reflection` entry with `weight=1.5` and
   `associations` pointing to the source entries.

Reflections surface recurring patterns and compress the memory store over time.

---

## `save_to_memory` Tool

Agents can explicitly request a memory save during any task using the
`save_to_memory` tool (registered in the OpenClaw `ToolRegistry`):

```json
{
  "type": "function",
  "function": {
    "name": "save_to_memory",
    "description": "Persist an important fact, insight, or piece of context to the Sapphire long-term memory store.",
    "parameters": {
      "type": "object",
      "properties": {
        "content": {
          "type": "string",
          "description": "The memory to store (a clear, self-contained statement)."
        },
        "weight": {
          "type": "number",
          "description": "Importance score 0.0–2.0 (default 1.0).",
          "default": 1.0
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Optional categorisation tags."
        }
      },
      "required": ["content"]
    }
  }
}
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/ai/chat` | Memory-augmented chat (Cognitive Wrapper) |
| `POST` | `/api/memory/save` | Manually save a memory entry |
| `POST` | `/api/memory/search` | Semantic search over stored memories |
| `GET` | `/api/memory/list` | List most-recent memories |
| `POST` | `/api/memory/reflect` | Trigger a manual reflection cycle |
| `DELETE` | `/api/memory/<id>` | Delete a memory entry by id |

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `./chroma_memory` | Local directory for ChromaDB data |
| `CHROMA_COLLECTION` | `sapphire` | ChromaDB collection name |
| `SAPPHIRE_MEMORY_TOP_K` | `5` | Memories retrieved per query |
| `SAPPHIRE_REFLECTION_INTERVAL` | `10` | Saves between auto-reflections (0 = off) |

---

## Precedence Rule

When retrieved context contradicts the `identity.md` file, the **Identity
Profile takes precedence**.  Memory augments identity — it does not override it.
