"""Session store — persists per-user conversation sessions.

The default implementation is in-memory (suitable for single-process
deployments and tests).  Swap in a Redis or database backend by replacing
the internal ``_store`` dict with a remote client.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class SessionStore:
    """Thread-safe in-memory session store.

    Each session is identified by a ``session_id`` string and holds:

    * ``messages``    — ordered list of ``{"role": str, "content": str}`` dicts.
    * ``metadata``    — arbitrary key→value store for session-level data.
    * ``created_at``  — UNIX timestamp of session creation.
    * ``updated_at``  — UNIX timestamp of the last write.

    Args:
        ttl: Session time-to-live in seconds.  Sessions idle longer than
             *ttl* are removed on the next :meth:`cleanup` call.
             Pass ``0`` to disable expiry.
    """

    def __init__(self, ttl: float = 3600.0) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl

    # ── Session lifecycle ─────────────────────────────────────────────────

    def get_or_create(self, session_id: str) -> Dict[str, Any]:
        """Return the existing session or create a fresh one."""
        if session_id not in self._store:
            self._store[session_id] = {
                "messages": [],
                "metadata": {},
                "created_at": time.time(),
                "updated_at": time.time(),
            }
        return self._store[session_id]

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the session if it exists, else *None*."""
        return self._store.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session.  Returns *True* if the session existed."""
        return self._store.pop(session_id, None) is not None

    # ── Message history ───────────────────────────────────────────────────

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session's history."""
        session = self.get_or_create(session_id)
        session["messages"].append({"role": role, "content": content, "ts": time.time()})
        session["updated_at"] = time.time()

    def get_messages(self, session_id: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Return messages for *session_id*, newest-last.

        Args:
            session_id: Session identifier.
            limit:      Maximum number of most-recent messages.  ``0`` = all.
        """
        session = self._store.get(session_id)
        if session is None:
            return []
        messages = session["messages"]
        return messages[-limit:] if limit > 0 else list(messages)

    def clear_messages(self, session_id: str) -> None:
        """Clear message history for a session (keeps metadata)."""
        session = self._store.get(session_id)
        if session:
            session["messages"] = []
            session["updated_at"] = time.time()

    # ── Metadata ──────────────────────────────────────────────────────────

    def set_meta(self, session_id: str, key: str, value: Any) -> None:
        session = self.get_or_create(session_id)
        session["metadata"][key] = value
        session["updated_at"] = time.time()

    def get_meta(self, session_id: str, key: str, default: Any = None) -> Any:
        session = self._store.get(session_id)
        if session is None:
            return default
        return session["metadata"].get(key, default)

    # ── Housekeeping ──────────────────────────────────────────────────────

    def cleanup(self) -> int:
        """Remove expired sessions.  Returns the number removed."""
        if self._ttl <= 0:
            return 0
        cutoff = time.time() - self._ttl
        expired = [sid for sid, s in self._store.items() if s["updated_at"] < cutoff]
        for sid in expired:
            del self._store[sid]
        return len(expired)

    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._store)
