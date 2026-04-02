"""Telegram channel adapter — converts Bot API updates into queue messages."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TelegramChannel:
    """Adapter for the Telegram Bot API.

    Call :meth:`handle_update` from your webhook handler (e.g. a Flask route
    or a ``python-telegram-bot`` callback) to normalise the update and enqueue
    it for processing.

    Args:
        dispatcher: A :class:`~gateway.dispatcher.Dispatcher` instance.
        bot_token:  Telegram Bot API token (used for outbound replies).
    """

    SOURCE = "telegram"

    def __init__(self, dispatcher=None, bot_token: str = "") -> None:
        self._dispatcher = dispatcher
        self._bot_token = bot_token

    async def handle_update(self, update: Dict[str, Any]) -> None:
        """Normalise a Telegram update and push it onto the dispatch queue.

        Args:
            update: Raw Bot API update object (as parsed JSON).
        """
        message = update.get("message") or update.get("edited_message")
        if not message:
            logger.debug("TelegramChannel: update has no message field — skipping")
            return

        content = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", ""))
        if not content or not chat_id:
            logger.debug("TelegramChannel: empty text or chat_id — skipping")
            return

        normalised = {
            "content": content,
            "session_id": chat_id,
            "source": self.SOURCE,
            "raw": message,
        }

        if self._dispatcher is not None:
            await self._dispatcher.dispatch(normalised)
        else:
            logger.warning("TelegramChannel: no dispatcher configured — message dropped")

    def send(self, chat_id: str, text: str) -> None:
        """Send a reply back to a Telegram chat.

        Requires the ``requests`` library.  In production, prefer the
        async ``telegram.Bot.send_message`` from ``python-telegram-bot``.

        Args:
            chat_id: Telegram chat / user identifier.
            text:    Message text to send.
        """
        try:
            import requests
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            resp.raise_for_status()
            logger.info("TelegramChannel: sent reply to chat_id=%s", chat_id)
        except Exception as exc:
            logger.error("TelegramChannel: send error: %s", exc)
