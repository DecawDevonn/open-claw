"""Multi-agent orchestrator — the heart of the OpenClaw message-processing pipeline.

Receives a normalised message, routes it to the correct agent, runs the
agent asynchronously, and delivers the response back through the messenger.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from gateway.router import route_message
from delivery.messenger import Messenger
from loggers.logger import log_info, log_error

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Coordinates routing, execution, and delivery for a single message.

    Usage::

        orchestrator = MultiAgentOrchestrator()
        await orchestrator.process_message(message)

    The *message* object must expose the following attributes:

    * ``content``    — raw message text
    * ``session_id`` — user / conversation identifier
    * ``source``     — originating channel name (e.g. ``"telegram"``)
    """

    def __init__(self, messenger: Messenger = None) -> None:
        self.messenger = messenger or Messenger()

    async def process_message(self, message: Any) -> None:
        """Route, run, and deliver a single message.

        On failure the orchestrator falls back to the default agent rather
        than surfacing a raw exception to the delivery layer.
        """
        try:
            agent = route_message(message)
            response = await self._run_agent(agent, message)
            self.messenger.send(response, message.source, message.session_id)
        except Exception as exc:
            log_error("MultiAgentOrchestrator: processing error: %s", exc)
            try:
                from agents.default_agent import DefaultAgent
                fallback = DefaultAgent()
                response = await self._run_agent(fallback, message)
                self.messenger.send(response, message.source, message.session_id)
            except Exception as fallback_exc:
                log_error("MultiAgentOrchestrator: fallback also failed: %s", fallback_exc)

    async def _run_agent(self, agent: Any, message: Any) -> str:
        """Execute *agent.process()* in a thread-pool executor.

        This allows blocking agent implementations (e.g. ones that call
        synchronous HTTP clients) to run without blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            agent.process,
            message.content,
            message.session_id,
        )
        log_info("MultiAgentOrchestrator: agent '%s' processed session=%s", agent.name, message.session_id)
        return response
