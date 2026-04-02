"""Lightweight in-process metrics collector for OpenClaw.

For production use, replace the in-memory counters with Prometheus, StatsD,
or any time-series back-end by swapping :class:`MetricsCollector`.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict


class MetricsCollector:
    """Thread-safe counter and gauge store.

    Example::

        metrics = MetricsCollector()
        metrics.increment("messages_received", tags={"channel": "telegram"})
        metrics.gauge("queue_depth", 42)
        print(metrics.snapshot())
    """

    def __init__(self) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._started_at: float = time.time()

    # ── Counters ──────────────────────────────────────────────────────────

    def increment(self, name: str, value: float = 1.0, tags: Dict[str, str] = None) -> None:
        """Increment a counter by *value*."""
        key = self._key(name, tags)
        self._counters[key] += value

    def decrement(self, name: str, value: float = 1.0, tags: Dict[str, str] = None) -> None:
        """Decrement a counter by *value*."""
        self.increment(name, -value, tags)

    def count(self, name: str, tags: Dict[str, str] = None) -> float:
        return self._counters[self._key(name, tags)]

    # ── Gauges ────────────────────────────────────────────────────────────

    def gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set a gauge to an absolute value."""
        self._gauges[self._key(name, tags)] = value

    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> float:
        return self._gauges.get(self._key(name, tags), 0.0)

    # ── Snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        return {
            "uptime_seconds": round(time.time() - self._started_at, 2),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _key(name: str, tags: Dict[str, str] = None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
