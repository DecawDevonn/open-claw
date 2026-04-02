"""Heartbeat — periodic background tasks for registered agents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, List

from loggers.logger import log_info

logger = logging.getLogger(__name__)


async def heartbeat_task(agent_list: List[Any], interval: float = 60.0) -> None:
    """Run the proactive task loop for each agent in *agent_list*.

    Calls :meth:`perform_proactive_tasks` on every agent that exposes it,
    then sleeps for *interval* seconds before repeating.

    Args:
        agent_list: List of agent instances to tick.
        interval:   Sleep duration in seconds between ticks (default 60 s).

    This coroutine runs forever; cancel the task to stop it::

        task = asyncio.create_task(heartbeat_task(agents))
        # ... later ...
        task.cancel()
    """
    while True:
        for agent in agent_list:
            try:
                if hasattr(agent, "perform_proactive_tasks"):
                    agent.perform_proactive_tasks()
                    log_info("Heartbeat: agent '%s' executed proactive tasks", agent.name)
            except Exception as exc:
                logger.error("Heartbeat: error in agent '%s': %s", getattr(agent, "name", "?"), exc)
        await asyncio.sleep(interval)
