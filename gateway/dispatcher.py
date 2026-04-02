"""Gateway dispatcher — enqueues inbound messages from any channel.

The dispatcher is the single entry-point for all inbound traffic.  Channels
call :meth:`Dispatcher.dispatch` with a normalised message dict; the
dispatcher serialises it onto the Redis queue so the queue consumer can
process it asynchronously.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Dispatcher:
    """Asynchronous message dispatcher.

    Args:
        queue: A :class:`~queues.redis_queue.RedisQueue` instance.
               If *None*, messages are logged but not enqueued (dry-run).
    """

    def __init__(self, queue=None) -> None:
        self._queue = queue

    async def dispatch(self, message: Dict[str, Any]) -> None:
        """Validate and enqueue a normalised message.

        Expected message keys:
            - ``content``    (str)  — message text
            - ``session_id`` (str)  — conversation / user identifier
            - ``source``     (str)  — originating channel name

        Args:
            message: Normalised message dictionary.

        Raises:
            ValueError: If required keys are missing.
        """
        for key in ("content", "session_id", "source"):
            if key not in message:
                raise ValueError(f"Dispatcher: message is missing required key '{key}'")

        if self._queue is None:
            logger.warning(
                "Dispatcher: no queue configured — dropping message from %s session=%s",
                message["source"],
                message["session_id"],
            )
            return

        await self._queue.enqueue(json.dumps(message))
        logger.info(
            "Dispatcher: enqueued message source=%s session=%s",
            message["source"],
            message["session_id"],
        )
