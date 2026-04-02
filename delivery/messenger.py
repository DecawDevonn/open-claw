"""Delivery messenger — sends agent responses back to the originating channel."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Channel registry: source name → channel adapter instance
_channels: Dict[str, Any] = {}


def register_channel(name: str, channel: Any) -> None:
    """Register a channel adapter under *name* (e.g. ``"telegram"``)."""
    _channels[name] = channel
    logger.debug("Messenger: registered channel '%s'", name)


class Messenger:
    """Routes outbound responses to the correct channel adapter.

    Usage::

        messenger = Messenger()
        messenger.send("Hello!", source="telegram", session_id="123456789")
    """

    def send(self, response: str, source: str, session_id: str) -> None:
        """Send *response* back to the user identified by *session_id* on *source*.

        Args:
            response:   Text to deliver to the user.
            source:     Channel name (e.g. ``"telegram"``, ``"slack"``, ``"web"``).
            session_id: User / chat / channel identifier within the source.
        """
        channel = _channels.get(source)
        if channel is None:
            logger.warning(
                "Messenger: no channel adapter registered for source='%s' — logging response only: %s",
                source,
                response[:120],
            )
            return

        try:
            # Each channel adapter exposes a synchronous or async send method
            if hasattr(channel, "send"):
                channel.send(session_id, response)
                logger.info("Messenger: delivered response to %s session=%s", source, session_id)
            else:
                logger.error("Messenger: channel '%s' has no send() method", source)
        except Exception as exc:
            logger.error("Messenger: delivery error for %s session=%s: %s", source, session_id, exc)
