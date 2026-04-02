"""start_server.py — launch the OpenClaw multi-agent system.

Usage::

    python scripts/start_server.py

The server starts the Flask API (via Gunicorn when available) alongside the
async queue consumer and orchestration heartbeat.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# Ensure the project root is on sys.path when run directly
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import get_settings
from orchestration.queue_consumer import queue_consumer
from orchestration.heartbeat import heartbeat_task
from orchestration.cron_scheduler import CronScheduler
from agents.default_agent import DefaultAgent
from agents.weather_agent import WeatherAgent
from agents.email_agent import EmailAgent
from gateway.router import register_agent, set_fallback
from loggers.logger import log_info

logger = logging.getLogger(__name__)


def _register_default_agents():
    """Wire up the built-in agents into the global router."""
    weather = WeatherAgent()
    email = EmailAgent()
    register_agent(weather)
    register_agent(email)
    default = DefaultAgent()
    set_fallback(default)
    log_info("start_server: registered agents: weather, email, default (fallback)")
    return [weather, email, default]


async def main():
    settings = get_settings()
    settings.warn_insecure_defaults()

    log_info("OpenClaw multi-agent system starting on %s:%d", settings.host, settings.port)

    agents = _register_default_agents()

    # Build cron scheduler
    scheduler = CronScheduler(tick=1.0)
    # Example: clean up idle sessions every 30 minutes
    # scheduler.add_job("session_cleanup", some_cleanup_fn, interval=1800)

    # Run all async background tasks concurrently
    await asyncio.gather(
        # Queue consumer (requires Redis — will error if Redis is not running)
        queue_consumer(
            host=settings.redis_url.split("://")[-1].split(":")[0] if "://" in settings.redis_url else "localhost",
            channel=settings.queue_channel,
        ),
        # Heartbeat — ticks every N seconds for proactive agent tasks
        heartbeat_task(agents, interval=settings.heartbeat_interval),
        # Cron scheduler
        scheduler.run(),
    )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    print("OpenClaw multi-agent system starting...")
    print("  Queue consumer + heartbeat + cron scheduler running.")
    print("  Start the Flask API separately:  gunicorn 'app:create_app()'")
    print("  Press Ctrl-C to stop.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested — bye.")
