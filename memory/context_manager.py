"""Context manager — builds a prompt-ready context window from session history."""

from __future__ import annotations

from typing import Dict, List, Optional

from .session_store import SessionStore


class ContextManager:
    """Assembles the conversation context that agents receive.

    Reads the rolling message history from a :class:`SessionStore`, optionally
    prepends a system prompt, and returns a list of ``{"role", "content"}``
    dicts ready for the OpenAI Chat Completions API (or any LLM that accepts
    that format).

    Args:
        session_store: Backing store for session history.
        max_messages:  Maximum number of recent messages to include in context.
        system_prompt: Default system prompt prepended to every context window.
    """

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        max_messages: int = 20,
        system_prompt: str = "You are a helpful AI assistant.",
    ) -> None:
        self._store = session_store or SessionStore()
        self._max_messages = max_messages
        self._system_prompt = system_prompt

    def build_context(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Return the context window for *session_id*.

        Args:
            session_id:    Session identifier.
            system_prompt: Override the default system prompt for this call.

        Returns:
            List of ``{"role": str, "content": str}`` dicts.
        """
        system = system_prompt or self._system_prompt
        messages = self._store.get_messages(session_id, limit=self._max_messages)
        context: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for msg in messages:
            context.append({"role": msg["role"], "content": msg["content"]})
        return context

    def add_user_message(self, session_id: str, content: str) -> None:
        """Append a user turn to the session history."""
        self._store.append_message(session_id, "user", content)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Append an assistant turn to the session history."""
        self._store.append_message(session_id, "assistant", content)

    def clear(self, session_id: str) -> None:
        """Reset the conversation history for a session."""
        self._store.clear_messages(session_id)

    def summarise(self, session_id: str, max_chars: int = 500) -> str:
        """Return a truncated plain-text summary of the conversation so far."""
        messages = self._store.get_messages(session_id)
        lines = [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
        text = "\n".join(lines)
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
