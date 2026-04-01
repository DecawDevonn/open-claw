import time
import threading
from typing import Dict, Any
from datetime import datetime, timezone


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
        self._start_time = time.time()

    def increment(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._start_time,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {
                        "count": len(v),
                        "sum": sum(v),
                        "avg": sum(v) / len(v) if v else 0,
                    }
                    for k, v in self._histograms.items()
                },
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }


# Global metrics instance
metrics = MetricsCollector()
