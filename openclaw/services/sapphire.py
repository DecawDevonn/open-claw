"""Sapphire Cognitive Wrapper — persistent vector memory using ChromaDB.

The Sapphire Protocol gives DEVONN.AI a continuous identity across interactions
by maintaining a local ChromaDB collection where every significant memory is
stored as a vector.

Key behaviours
--------------
* ``save``   — Embed and persist a memory entry (id, content, weight, tags).
* ``search`` — Query nearest-neighbour memories and return them ranked by
               relevance (cosine similarity).
* ``inject`` — Retrieve relevant context and return a formatted block that
               can be prepended to any LLM system prompt.
* ``reflect``— Summarise the most-recent N memories into a single "reflection"
               entry that is itself saved back to the store.  Called
               automatically every ``reflection_interval`` saves.
* ``delete`` / ``list`` — Housekeeping helpers.

ChromaDB is an optional dependency.  When it is not installed the service
degrades gracefully by keeping an in-process fallback store so tests and
environments without ChromaDB still work.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── ChromaDB import (graceful fallback) ───────────────────────────────────────

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CHROMA_AVAILABLE = False
    chromadb = None  # type: ignore[assignment]
    ChromaSettings = None  # type: ignore[assignment]


# ── Fallback in-process store ─────────────────────────────────────────────────

class _FallbackStore:
    """Minimal in-memory store used when ChromaDB is not installed."""

    def __init__(self) -> None:
        self._docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, entry: Dict[str, Any]) -> None:
        self._docs[entry["id"]] = entry

    def query(self, _vector: List[float], n: int) -> List[Dict[str, Any]]:
        results = sorted(self._docs.values(), key=lambda d: d.get("ts", 0), reverse=True)
        return results[:n]

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        return self._docs.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        return self._docs.pop(memory_id, None) is not None

    def list_all(self) -> List[Dict[str, Any]]:
        return sorted(self._docs.values(), key=lambda d: d.get("ts", 0), reverse=True)

    def count(self) -> int:
        return len(self._docs)


# ── SapphireMemory ─────────────────────────────────────────────────────────────

class SapphireMemory:
    """Persistent vector memory store for the DEVONN.AI Sapphire Protocol.

    Parameters
    ----------
    persist_dir:
        Path to the directory where ChromaDB will persist its data.
        Defaults to ``./chroma_memory``.
    collection_name:
        ChromaDB collection name.  Defaults to ``'sapphire'``.
    ai_service:
        An :class:`~openclaw.services.ai.AIService` instance used to generate
        embedding vectors.  When *None* a deterministic hash-based fallback is
        used (suitable for tests).
    top_k:
        Number of memories returned by :meth:`search` / :meth:`inject`.
    reflection_interval:
        After every N calls to :meth:`save` the wrapper automatically calls
        :meth:`reflect` to compress the most-recent memories.
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_memory",
        collection_name: str = "sapphire",
        ai_service: Optional[Any] = None,
        top_k: int = 5,
        reflection_interval: int = 10,
    ) -> None:
        self._ai = ai_service
        self._top_k = top_k
        self._reflection_interval = reflection_interval
        self._save_count = 0

        if _CHROMA_AVAILABLE:
            try:
                client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                self._collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._fallback: Optional[_FallbackStore] = None
                logger.info("SapphireMemory: ChromaDB initialised at %s", persist_dir)
            except Exception as exc:
                logger.warning("SapphireMemory: ChromaDB init failed (%s); using fallback.", exc)
                self._collection = None
                self._fallback = _FallbackStore()
        else:
            logger.warning("SapphireMemory: chromadb not installed; using in-process fallback.")
            self._collection = None
            self._fallback = _FallbackStore()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> List[float]:
        """Return an embedding vector for *text*."""
        if self._ai is not None:
            try:
                return self._ai.embed(text)
            except Exception as exc:
                logger.warning("SapphireMemory: embed failed (%s); using hash fallback.", exc)
        # Deterministic 128-dim hash vector used as fallback when no AI service is available
        # (e.g. in tests or environments without an OpenAI key).
        # NOTE: this dimensionality (128) differs from real OpenAI embeddings
        # (1536 for text-embedding-3-small).  The fallback store (_FallbackStore)
        # does not perform true nearest-neighbour search, so the mismatch is
        # harmless — it is purely used for ID generation/ordering.  Do NOT
        # mix hash-based and real embeddings in the same ChromaDB collection.
        digest = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) * 2 - 1 for b in digest[:128]]

    def _metadata_for(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "content": entry["content"],
            "weight": float(entry.get("weight", 1.0)),
            "tags": json.dumps(entry.get("tags", [])),
            "ts": entry.get("ts", time.time()),
            "associations": json.dumps(entry.get("associations", [])),
            "type": entry.get("type", "memory"),
        }

    # ── Core API ──────────────────────────────────────────────────────────────

    def save(
        self,
        content: str,
        memory_id: Optional[str] = None,
        weight: float = 1.0,
        tags: Optional[List[str]] = None,
        associations: Optional[List[str]] = None,
        memory_type: str = "memory",
    ) -> str:
        """Embed *content* and persist it as a memory entry.

        Returns the memory id.
        """
        mid = memory_id or str(uuid.uuid4())
        entry: Dict[str, Any] = {
            "id": mid,
            "content": content,
            "weight": weight,
            "tags": tags or [],
            "associations": associations or [],
            "ts": time.time(),
            "type": memory_type,
        }
        vector = self._embed(content)

        if self._collection is not None:
            try:
                self._collection.upsert(
                    ids=[mid],
                    embeddings=[vector],
                    documents=[content],
                    metadatas=[self._metadata_for(entry)],
                )
            except Exception as exc:
                logger.error("SapphireMemory.save: ChromaDB upsert failed: %s", exc)
                raise
        else:
            assert self._fallback is not None
            self._fallback.upsert(entry)

        self._save_count += 1
        if self._reflection_interval > 0 and self._save_count % self._reflection_interval == 0:
            self._auto_reflect()

        logger.debug("SapphireMemory: saved memory %s", mid)
        return mid

    def search(self, query: str, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return the top-*n* most relevant memories for *query*."""
        k = n or self._top_k
        vector = self._embed(query)

        if self._collection is not None:
            try:
                results = self._collection.query(
                    query_embeddings=[vector],
                    n_results=min(k, self._collection.count() or 1),
                    include=["documents", "metadatas", "distances"],
                )
                memories = []
                ids = results.get("ids", [[]])[0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]
                for mid, doc, meta, dist in zip(ids, docs, metas, dists):
                    memories.append({
                        "id": mid,
                        "content": doc,
                        "weight": meta.get("weight", 1.0),
                        "tags": json.loads(meta.get("tags", "[]")),
                        "associations": json.loads(meta.get("associations", "[]")),
                        "ts": meta.get("ts"),
                        "type": meta.get("type", "memory"),
                        "relevance": round(1 - float(dist), 4),
                    })
                return memories
            except Exception as exc:
                logger.error("SapphireMemory.search: ChromaDB query failed: %s", exc)
                return []
        else:
            assert self._fallback is not None
            return self._fallback.query(vector, k)

    def inject(self, query: str, n: Optional[int] = None) -> str:
        """Return a formatted memory block to prepend to a system prompt.

        Returns an empty string when no relevant memories exist.
        """
        memories = self.search(query, n=n)
        if not memories:
            return ""
        lines = ["[SAPPHIRE MEMORY — retrieved context]"]
        for m in memories:
            ts = m.get("ts")
            ts_str = f" (ts={ts:.0f})" if ts else ""
            lines.append(f"- {m['content']}{ts_str}")
        lines.append("[END MEMORY]")
        return "\n".join(lines)

    def reflect(self, n: int = 5) -> Optional[str]:
        """Summarise the most-recent *n* memories and save the summary.

        Returns the id of the saved reflection, or None if there are fewer
        than 2 memories or no AI service is available.
        """
        recent = self.list(limit=n)
        if len(recent) < 2:
            return None
        if self._ai is None:
            return None

        content_block = "\n".join(f"- {m['content']}" for m in recent)
        prompt = (
            "You are DEVONN.AI's memory reflection engine.\n"
            "Summarise these recent memory entries into a single concise insight "
            "that captures recurring patterns, key facts, or important context.\n\n"
            f"Memories:\n{content_block}\n\nSummary:"
        )
        try:
            summary = self._ai.complete(
                prompt=prompt,
                system="You are a memory compression engine. Be concise.",
                max_tokens=200,
                temperature=0.3,
            )
        except Exception as exc:
            logger.warning("SapphireMemory.reflect: AI summarisation failed: %s", exc)
            return None

        mid = self.save(
            content=summary.strip(),
            weight=1.5,
            tags=["reflection"],
            associations=[m["id"] for m in recent],
            memory_type="reflection",
        )
        logger.info("SapphireMemory: reflection saved as %s", mid)
        return mid

    def delete(self, memory_id: str) -> bool:
        """Remove a memory entry by id.  Returns True if it existed."""
        if self._collection is not None:
            try:
                existing = self._collection.get(ids=[memory_id], include=[])
                if not existing.get("ids"):
                    return False
                self._collection.delete(ids=[memory_id])
                return True
            except Exception:
                return False
        else:
            assert self._fallback is not None
            return self._fallback.delete(memory_id)

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return up to *limit* most-recent memories (newest first)."""
        if self._collection is not None:
            try:
                total = self._collection.count()
                if total == 0:
                    return []
                results = self._collection.get(
                    include=["documents", "metadatas"],
                )
                ids = results.get("ids", [])
                docs = results.get("documents", [])
                metas = results.get("metadatas", [])
                memories = []
                for mid, doc, meta in zip(ids, docs, metas):
                    memories.append({
                        "id": mid,
                        "content": doc,
                        "weight": meta.get("weight", 1.0),
                        "tags": json.loads(meta.get("tags", "[]")),
                        "associations": json.loads(meta.get("associations", "[]")),
                        "ts": meta.get("ts"),
                        "type": meta.get("type", "memory"),
                    })
                memories.sort(key=lambda m: m.get("ts") or 0, reverse=True)
                return memories[:limit]
            except Exception as exc:
                logger.error("SapphireMemory.list: ChromaDB get failed: %s", exc)
                return []
        else:
            assert self._fallback is not None
            return self._fallback.list_all()[:limit]

    def count(self) -> int:
        """Return total number of stored memories."""
        if self._collection is not None:
            try:
                return self._collection.count()
            except Exception:
                return 0
        else:
            assert self._fallback is not None
            return self._fallback.count()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _auto_reflect(self) -> None:
        """Trigger reflection silently; errors are logged but not raised."""
        try:
            self.reflect()
        except Exception as exc:
            logger.warning("SapphireMemory: auto-reflect failed: %s", exc)


# ── save_to_memory tool JSON Schema ──────────────────────────────────────────

SAVE_TO_MEMORY_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "save_to_memory",
        "description": (
            "Persist an important fact, insight, or piece of context to the "
            "Sapphire long-term memory store.  Call this whenever you learn "
            "something that should be remembered across future conversations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The memory to store (a clear, self-contained statement).",
                },
                "weight": {
                    "type": "number",
                    "description": "Importance score 0.0–2.0 (default 1.0).",
                    "default": 1.0,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional categorisation tags.",
                },
            },
            "required": ["content"],
        },
    },
}
