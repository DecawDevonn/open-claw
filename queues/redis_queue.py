"""Async Redis-backed message queue.

Uses the ``redis`` package (>=4.2) which ships ``redis.asyncio`` natively.
Install with: ``pip install redis``.

Fallback stubs are provided so the rest of the codebase can import and test
this module even when Redis is not installed.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis  # redis>=4.2
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False


class RedisQueue:
    """Async FIFO queue backed by a Redis list.

    Each queue is a named Redis list.  :meth:`enqueue` appends to the right;
    :meth:`dequeue` pops from the left (FIFO order).

    Args:
        channel: Redis list key name used as the queue.
        host:    Redis host (default ``localhost``).
        port:    Redis port (default ``6379``).
        db:      Redis database index (default ``0``).
        password: Optional Redis password.
    """

    def __init__(
        self,
        channel: str = "openclaw:messages",
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
    ) -> None:
        if not channel or not channel.strip():
            raise ValueError("RedisQueue channel name must not be empty")
        self.channel = channel
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._redis: Optional[Any] = None

    # ── Connection lifecycle ───────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the async connection pool to Redis."""
        if not _REDIS_AVAILABLE:
            raise RuntimeError(
                "redis package is not installed. "
                "Run: pip install redis"
            )
        self._redis = await aioredis.from_url(
            f"redis://{self._host}:{self._port}/{self._db}",
            password=self._password,
            decode_responses=True,
        )
        logger.info("RedisQueue connected: channel=%s host=%s port=%s", self.channel, self._host, self._port)

    async def close(self) -> None:
        """Close the Redis connection pool gracefully."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    # ── Queue operations ──────────────────────────────────────────────────

    async def enqueue(self, message: Any) -> None:
        """Serialise *message* to JSON and push it onto the queue."""
        self._assert_connected()
        payload = json.dumps(message) if not isinstance(message, str) else message
        await self._redis.rpush(self.channel, payload)

    async def dequeue(self) -> Optional[Any]:
        """Pop the oldest message from the queue.

        Returns the deserialised message, or *None* if the queue is empty.
        """
        self._assert_connected()
        raw = await self._redis.lpop(self.channel)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def length(self) -> int:
        """Return the current queue depth."""
        self._assert_connected()
        return await self._redis.llen(self.channel)

    async def clear(self) -> None:
        """Remove all messages from the queue."""
        self._assert_connected()
        await self._redis.delete(self.channel)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _assert_connected(self) -> None:
        if self._redis is None:
            raise RuntimeError("RedisQueue is not connected. Call await queue.connect() first.")
