"""Web channel adapter — accepts plain JSON messages from an HTTP endpoint."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

logger = logging.getLogger(__name__)


class WebChannel:
    """Adapter for the REST/WebSocket web interface.

    In a Flask application, call :meth:`handle_request` from a route handler:

    .. code-block:: python

        @app.route("/api/chat", methods=["POST"])
        async def chat():
            body = request.get_json()
            await web_channel.handle_request(body)
            return jsonify({"status": "queued"})

    Args:
        dispatcher: A :class:`~gateway.dispatcher.Dispatcher` instance.
    """

    SOURCE = "web"

    def __init__(self, dispatcher=None) -> None:
        self._dispatcher = dispatcher

    async def handle_request(self, body: Dict[str, Any]) -> str:
        """Normalise an HTTP JSON body and enqueue it.

        Expected body keys:
            - ``message``    (required) — message text
            - ``session_id`` (optional) — a UUID is generated if omitted

        Args:
            body: Parsed JSON request body.

        Returns:
            The resolved ``session_id`` for the message.

        Raises:
            ValueError: If ``message`` is missing or empty.
        """
        content = body.get("message", "").strip()
        if not content:
            raise ValueError("WebChannel: 'message' field is required and must not be empty")

        session_id = str(body.get("session_id", "") or uuid.uuid4())

        normalised = {
            "content": content,
            "session_id": session_id,
            "source": self.SOURCE,
            "raw": body,
        }

        if self._dispatcher is not None:
            await self._dispatcher.dispatch(normalised)
        else:
            logger.warning("WebChannel: no dispatcher configured — message dropped for session=%s", session_id)

        return session_id
