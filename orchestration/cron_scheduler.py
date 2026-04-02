"""Cron scheduler — run callable tasks on a fixed time interval."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


@dataclass
class CronJob:
    """A registered scheduled job."""

    name: str
    fn: Callable[[], Any]
    interval: float             # seconds between invocations
    _next_run: float = field(default=0.0, init=False)

    def is_due(self, now: float) -> bool:
        return now >= self._next_run

    def mark_ran(self, now: float) -> None:
        self._next_run = now + self.interval


class CronScheduler:
    """Simple async interval-based task scheduler.

    Register callables with :meth:`add_job` and then ``await run()`` to start
    the scheduling loop.  Each job fires when its interval has elapsed.

    Example::

        scheduler = CronScheduler()
        scheduler.add_job("cleanup", cleanup_old_sessions, interval=3600)
        await scheduler.run()
    """

    def __init__(self, tick: float = 1.0) -> None:
        """
        Args:
            tick: How often (in seconds) the scheduler wakes to check for due jobs.
        """
        self._jobs: Dict[str, CronJob] = {}
        self._tick = tick
        self._running = False

    def add_job(
        self,
        name: str,
        fn: Callable[[], Any],
        interval: float,
    ) -> None:
        """Register a new job.

        Args:
            name:     Unique job identifier (used in logs).
            fn:       Zero-argument callable to invoke on each tick.
            interval: Minimum seconds between successive invocations.
        """
        self._jobs[name] = CronJob(name=name, fn=fn, interval=interval)
        logger.info("CronScheduler: registered job '%s' every %.0f s", name, interval)

    def remove_job(self, name: str) -> None:
        """Remove a registered job by name."""
        self._jobs.pop(name, None)

    async def run(self) -> None:
        """Start the scheduling loop (runs until cancelled)."""
        import time
        self._running = True
        logger.info("CronScheduler: started with %d job(s)", len(self._jobs))
        while self._running:
            now = time.time()
            for job in list(self._jobs.values()):
                if job.is_due(now):
                    try:
                        result = job.fn()
                        if asyncio.iscoroutine(result):
                            await result
                        job.mark_ran(now)
                        logger.debug("CronScheduler: ran job '%s'", job.name)
                    except Exception as exc:
                        logger.error("CronScheduler: job '%s' raised: %s", job.name, exc)
                        job.mark_ran(now)   # still advance to avoid tight error loops
            await asyncio.sleep(self._tick)

    def stop(self) -> None:
        """Signal the scheduler to stop after the current tick."""
        self._running = False
