"""Default fallback agent — handles any message that no specialised agent claimed."""

from __future__ import annotations

import logging
from typing import List

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DefaultAgent(BaseAgent):
    """Fallback agent used when no other agent matches the inbound message.

    Returns a generic acknowledgement so the user always receives a reply.
    Integrate an LLM call here for fully conversational fallback behaviour.
    """

    name: str = "default"
    keywords: List[str] = []          # matches everything

    def process(self, content: str, session_id: str) -> str:
        logger.info("DefaultAgent handling session=%s", session_id)
        return (
            "I received your message. I'm the default agent — "
            "please try a more specific command or check available capabilities."
        )
