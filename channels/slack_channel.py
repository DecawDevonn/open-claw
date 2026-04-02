"""Slack channel adapter — handles Slack Events API payloads."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SlackChannel:
    """Adapter for the Slack Events API.

    Wire up :meth:`handle_event` to your Slack app's event subscription
    endpoint.  The adapter normalises ``message`` events and pushes them
    onto the dispatch queue.

    Args:
        dispatcher:   A :class:`~gateway.dispatcher.Dispatcher` instance.
        signing_secret: Slack signing secret for request verification (optional).
    """

    SOURCE = "slack"

    def __init__(self, dispatcher=None, signing_secret: str = "") -> None:
        self._dispatcher = dispatcher
        self._signing_secret = signing_secret

    async def handle_event(self, payload: Dict[str, Any]) -> None:
        """Normalise a Slack Events API payload and enqueue it.

        Handles ``message`` sub-type events.  Bot messages are silently
        ignored to prevent feedback loops.

        Args:
            payload: Parsed JSON body from the Slack Events API.
        """
        event = payload.get("event", {})
        event_type = event.get("type", "")
        if event_type != "message":
            logger.debug("SlackChannel: ignoring event type '%s'", event_type)
            return

        # Ignore bot / system messages
        if event.get("bot_id") or event.get("subtype"):
            return

        content = event.get("text", "")
        channel_id = event.get("channel", "")
        user_id = event.get("user", channel_id)

        if not content or not channel_id:
            logger.debug("SlackChannel: empty text or channel — skipping")
            return

        normalised = {
            "content": content,
            "session_id": user_id,
            "source": self.SOURCE,
            "channel": channel_id,
            "raw": event,
        }

        if self._dispatcher is not None:
            await self._dispatcher.dispatch(normalised)
        else:
            logger.warning("SlackChannel: no dispatcher configured — message dropped")
