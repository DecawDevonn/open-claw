"""Agent memory — per-agent context / short-term and long-term store."""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional


class AgentMemory:
    """Lightweight per-agent memory store.

    Keeps a sliding window of recent context entries (short-term) and an
    unbounded key→value fact store (long-term).  Both are in-process and
    intentionally simple — they can be replaced with a vector DB or Redis
    by swapping the backing store passed to the constructor.
    """

    def __init__(self, window: int = 20) -> None:
        self._window = window
        self._short_term: Deque[Dict[str, Any]] = deque(maxlen=window)
        self._long_term: Dict[str, Any] = {}

    # ── Short-term (sliding context window) ───────────────────────────────

    def remember(self, role: str, content: Any) -> None:
        """Append an entry to the short-term context window."""
        self._short_term.append({"role": role, "content": content})

    def context(self) -> List[Dict[str, Any]]:
        """Return a snapshot of the current short-term context."""
        return list(self._short_term)

    def clear_context(self) -> None:
        self._short_term.clear()

    # ── Long-term (fact store) ─────────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        """Persist a named fact to long-term memory."""
        self._long_term[key] = value

    def recall(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a fact from long-term memory."""
        return self._long_term.get(key, default)

    def facts(self) -> Dict[str, Any]:
        """Return a copy of all stored facts."""
        return dict(self._long_term)

    def clear_facts(self) -> None:
        self._long_term.clear()

    # ── Combined snapshot ─────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        return {
            "context": self.context(),
            "facts": self.facts(),
        }
