"""Email agent — composes and dispatches emails on behalf of the operator."""

from __future__ import annotations

import logging
from typing import List

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EmailAgent(BaseAgent):
    """Handles email-related requests (compose, send, summarise inbox).

    Delegates actual sending to :class:`tools.email_tool.EmailTool`.  Import
    and wire a tool instance at construction time to enable live sending.
    """

    name: str = "email"
    keywords: List[str] = ["email", "send mail", "compose", "inbox", "reply", "forward"]

    def __init__(self, email_tool=None) -> None:
        """
        Args:
            email_tool: An :class:`tools.email_tool.EmailTool` instance (optional).
                        If *None*, the agent operates in dry-run mode and logs
                        what it *would* send without actually sending it.
        """
        self._tool = email_tool

    def process(self, content: str, session_id: str) -> str:
        logger.info("EmailAgent handling session=%s", session_id)
        recipient, subject, body = self._parse_request(content)
        if self._tool is None:
            logger.warning("EmailAgent: no email_tool configured — dry-run mode")
            return (
                f"[Dry-run] Would send email to {recipient!r} "
                f"with subject {subject!r}."
            )
        try:
            result = self._tool.execute(to=recipient, subject=subject, body=body)
            return f"Email sent to {recipient}. {result}"
        except Exception as exc:
            logger.error("EmailAgent send error: %s", exc)
            return f"Failed to send email: {exc}"

    def perform_proactive_tasks(self) -> None:
        """Placeholder: poll inbox, send scheduled digests, etc."""
        logger.debug("EmailAgent heartbeat tick — inbox polling not yet configured")

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _parse_request(content: str):
        """Minimal intent parser — replace with NLP for production use."""
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        to = "unknown@example.com"
        subject = "OpenClaw automated message"
        body = content
        for line in lines:
            lower = line.lower()
            if lower.startswith("to:"):
                to = line[3:].strip()
            elif lower.startswith("subject:"):
                subject = line[8:].strip()
        return to, subject, body
