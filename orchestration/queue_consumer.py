"""Queue consumer — continuously dequeues messages and dispatches them.

Run this as the entry point of your worker process::

    python scripts/start_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from queues.redis_queue import RedisQueue
from orchestration.multi_agent_orchestrator import MultiAgentOrchestrator
from loggers.logger import log_info, log_error

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 0.1  # seconds between queue polls when idle


class _Message:
    """Thin wrapper that converts a dict into an attribute-access object."""

    __slots__ = ("content", "session_id", "source", "raw")

    def __init__(self, data: dict) -> None:
        self.content: str = data.get("content", "")
        self.session_id: str = data.get("session_id", "anonymous")
        self.source: str = data.get("source", "unknown")
        self.raw: dict = data


async def queue_consumer(
    queue: Optional[RedisQueue] = None,
    orchestrator: Optional[MultiAgentOrchestrator] = None,
    host: str = "localhost",
    port: int = 6379,
    channel: str = "openclaw:messages",
) -> None:
    """Consume messages from Redis and process each through the orchestrator.

    Args:
        queue:        Pre-connected :class:`~queues.redis_queue.RedisQueue`.
                      If *None*, a new queue is created and connected using
                      *host* / *port* / *channel*.
        orchestrator: Pre-wired :class:`~orchestration.multi_agent_orchestrator.MultiAgentOrchestrator`.
                      A default instance is created if *None*.
        host:         Redis host (used only when *queue* is *None*).
        port:         Redis port (used only when *queue* is *None*).
        channel:      Redis list key (used only when *queue* is *None*).
    """
    if queue is None:
        queue = RedisQueue(channel=channel, host=host, port=port)
        await queue.connect()

    if orchestrator is None:
        orchestrator = MultiAgentOrchestrator()

    log_info("QueueConsumer: listening on channel='%s'", channel)

    while True:
        try:
            raw = await queue.dequeue()
            if raw is not None:
                data = raw if isinstance(raw, dict) else json.loads(raw)
                message = _Message(data)
                await orchestrator.process_message(message)
        except Exception as exc:
            log_error("QueueConsumer: unhandled error: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)
