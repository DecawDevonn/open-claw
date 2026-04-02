"""Gateway router — maps inbound messages to the most appropriate agent.

The routing strategy is intentionally simple: keyword matching with a
registered fallback.  Replace :func:`route_message` with an LLM-based
intent classifier for production use.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ── Global agent registry ─────────────────────────────────────────────────────

_registry: List["BaseAgent"] = []
_fallback: Optional["BaseAgent"] = None


def register_agent(agent: "BaseAgent") -> None:
    """Add *agent* to the global routing registry."""
    _registry.append(agent)
    logger.debug("Router: registered agent '%s'", agent.name)


def set_fallback(agent: "BaseAgent") -> None:
    """Set the agent used when no keyword match is found."""
    global _fallback
    _fallback = agent
    logger.debug("Router: fallback set to '%s'", agent.name)


def route_message(message: Any) -> "BaseAgent":
    """Return the most appropriate agent for *message*.

    Routing order:
    1. Exact keyword match against registered agents (case-insensitive).
    2. Fallback agent (if set).
    3. A :class:`~agents.default_agent.DefaultAgent` instance (auto-created).

    Args:
        message: Any object with a ``content`` attribute (string text).
    """
    content: str = getattr(message, "content", "") or ""
    content_lower = content.lower()

    for agent in _registry:
        for keyword in getattr(agent, "keywords", []):
            if keyword.lower() in content_lower:
                logger.debug("Router: matched agent '%s' on keyword '%s'", agent.name, keyword)
                return agent

    if _fallback is not None:
        logger.debug("Router: no keyword match — using fallback agent '%s'", _fallback.name)
        return _fallback

    # Auto-create a DefaultAgent so routing never returns None
    from agents.default_agent import DefaultAgent
    logger.debug("Router: no fallback set — creating DefaultAgent on demand")
    return DefaultAgent()
