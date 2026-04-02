"""Base agent — all OpenClaw agent implementations inherit from this class."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseAgent:
    """Abstract base for all OpenClaw agents.

    Subclasses must implement :meth:`process` and optionally
    :meth:`perform_proactive_tasks` for scheduled background work.
    """

    #: Override in subclasses to give agents a human-readable identity.
    name: str = "base"
    #: Keyword patterns that trigger this agent (used by the router).
    keywords: List[str] = []

    def process(self, content: str, session_id: str) -> str:
        """Process an inbound message and return a reply.

        Args:
            content: The raw message text from the user.
            session_id: Unique identifier for the user/conversation session.

        Returns:
            A string reply to send back through the delivery layer.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement process()")

    def perform_proactive_tasks(self) -> None:
        """Run scheduled / heartbeat tasks (optional).

        Called by the orchestration heartbeat on each tick.  The default
        implementation is a no-op; override in subclasses that need
        background activity (e.g. checking inboxes, polling APIs).
        """

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary of this agent."""
        return {
            "name": self.name,
            "keywords": self.keywords,
            "type": self.__class__.__name__,
        }
