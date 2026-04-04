"""
OpenClaw Metrics — lightweight in-process metrics collector.
Tracks request counts, latencies, and error rates per endpoint.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Any

_lock = threading.Lock()
_counters: Dict[str, int] = defaultdict(int)
_latencies: Dict[str, list] = defaultdict(list)
_started_at: float = time.time()


def record(endpoint: str, status_code: int, duration_ms: float) -> None:
    """Record a single request observation."""
    with _lock:
        _counters[f"{endpoint}:total"] += 1
        _counters[f"{endpoint}:{status_code}"] += 1
        _latencies[endpoint].append(duration_ms)
        # Keep only last 1000 samples per endpoint
        if len(_latencies[endpoint]) > 1000:
            _latencies[endpoint] = _latencies[endpoint][-1000:]


def snapshot() -> Dict[str, Any]:
    """Return a point-in-time snapshot of all metrics."""
    with _lock:
        uptime = time.time() - _started_at
        endpoints: Dict[str, Any] = {}
        for key, count in _counters.items():
            ep, code = key.rsplit(":", 1)
            if ep not in endpoints:
                endpoints[ep] = {"total": 0, "errors": 0, "p50_ms": 0, "p95_ms": 0}
            if code == "total":
                endpoints[ep]["total"] = count
            elif int(code) >= 400:
                endpoints[ep]["errors"] += count

        for ep, lats in _latencies.items():
            if lats and ep in endpoints:
                sorted_lats = sorted(lats)
                n = len(sorted_lats)
                endpoints[ep]["p50_ms"] = round(sorted_lats[int(n * 0.50)], 1)
                endpoints[ep]["p95_ms"] = round(sorted_lats[min(int(n * 0.95), n - 1)], 1)

        total_requests = sum(v for k, v in _counters.items() if k.endswith(":total"))
        total_errors = sum(v for k, v in _counters.items()
                           if not k.endswith(":total") and int(k.split(":")[-1]) >= 400)

        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate_pct": round(total_errors / max(total_requests, 1) * 100, 2),
            "endpoints": endpoints,
        }
