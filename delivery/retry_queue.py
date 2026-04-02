"""Delivery retry queue — re-enqueues failed outbound messages for later retry."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

logger = logging.getLogger(__name__)


@dataclass
class RetryEntry:
    """A single failed delivery that is awaiting retry."""

    response: str
    source: str
    session_id: str
    attempts: int = 0
    max_attempts: int = 3
    next_retry_at: float = field(default_factory=time.time)

    def should_retry(self) -> bool:
        return self.attempts < self.max_attempts and time.time() >= self.next_retry_at

    def record_failure(self, backoff: float = 5.0) -> None:
        self.attempts += 1
        self.next_retry_at = time.time() + backoff * (2 ** (self.attempts - 1))


class RetryQueue:
    """In-process retry queue for failed outbound deliveries.

    On failure, the messenger can hand the message to this queue.  A
    background task calls :meth:`flush` periodically to re-attempt delivery.

    Args:
        messenger: A :class:`~delivery.messenger.Messenger` instance used
                   for re-delivery attempts.
        max_size:  Maximum entries to hold (oldest are dropped when full).
    """

    def __init__(self, messenger=None, max_size: int = 1000) -> None:
        self._messenger = messenger
        self._queue: Deque[RetryEntry] = deque(maxlen=max_size)

    def enqueue(
        self,
        response: str,
        source: str,
        session_id: str,
        max_attempts: int = 3,
    ) -> None:
        """Add a failed delivery to the retry queue."""
        entry = RetryEntry(
            response=response,
            source=source,
            session_id=session_id,
            max_attempts=max_attempts,
        )
        self._queue.append(entry)
        logger.warning(
            "RetryQueue: queued failed delivery to %s session=%s (attempt 0/%d)",
            source,
            session_id,
            max_attempts,
        )

    def flush(self) -> int:
        """Attempt re-delivery for all due entries.

        Returns:
            Number of entries successfully delivered.
        """
        if self._messenger is None:
            return 0

        delivered = 0
        remaining: Deque[RetryEntry] = deque()

        while self._queue:
            entry = self._queue.popleft()
            if entry.should_retry():
                try:
                    self._messenger.send(entry.response, entry.source, entry.session_id)
                    delivered += 1
                    logger.info("RetryQueue: re-delivered to %s session=%s", entry.source, entry.session_id)
                except Exception as exc:
                    entry.record_failure()
                    logger.error("RetryQueue: retry failed for %s session=%s: %s", entry.source, entry.session_id, exc)
                    if entry.attempts < entry.max_attempts:
                        remaining.append(entry)
                    else:
                        logger.error("RetryQueue: max retries exceeded — dropping delivery for %s session=%s",
                                     entry.source, entry.session_id)
            else:
                remaining.append(entry)

        self._queue.extend(remaining)
        return delivered

    def size(self) -> int:
        return len(self._queue)
