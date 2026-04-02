"""Email tool — sends emails via SendGrid or SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class EmailTool(BaseTool):
    """Sends an email using SendGrid (preferred) or SMTP (fallback).

    Environment variables:

    * ``SENDGRID_API_KEY``    — SendGrid API key (enables SendGrid path).
    * ``SENDGRID_FROM_EMAIL`` — Verified sender address for SendGrid.
    * ``SMTP_HOST``           — SMTP server host (fallback).
    * ``SMTP_PORT``           — SMTP server port (default 587).
    * ``SMTP_USER``           — SMTP username.
    * ``SMTP_PASSWORD``       — SMTP password.
    * ``SMTP_FROM_EMAIL``     — Sender address for SMTP.
    """

    name: str = "send_email"
    description: str = "Send an email to a recipient via SendGrid or SMTP."

    def __init__(
        self,
        sendgrid_key: Optional[str] = None,
        sendgrid_from: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: Optional[str] = None,
    ) -> None:
        self._sg_key = sendgrid_key or os.getenv("SENDGRID_API_KEY", "")
        self._sg_from = sendgrid_from or os.getenv("SENDGRID_FROM_EMAIL", "")
        self._smtp_host = smtp_host or os.getenv("SMTP_HOST", "")
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self._smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self._smtp_from = smtp_from or os.getenv("SMTP_FROM_EMAIL", "")

    def validate(self, **kwargs: Any) -> None:
        for key in ("to", "subject", "body"):
            if not kwargs.get(key):
                raise ValueError(f"EmailTool: '{key}' is required")

    def execute(self, to: str, subject: str, body: str, html: Optional[str] = None, **kwargs: Any) -> str:
        """Send an email.

        Args:
            to:      Recipient email address.
            subject: Email subject line.
            body:    Plain-text email body.
            html:    Optional HTML body (used for rich emails via SendGrid).

        Returns:
            ``"sent:sendgrid"`` or ``"sent:smtp"`` on success.
        """
        if self._sg_key:
            return self._send_sendgrid(to, subject, body, html)
        if self._smtp_host:
            return self._send_smtp(to, subject, body)
        raise RuntimeError("EmailTool: neither SendGrid nor SMTP is configured")

    # ── Private helpers ────────────────────────────────────────────────────

    def _send_sendgrid(self, to: str, subject: str, body: str, html: Optional[str]) -> str:
        import requests
        payload: Dict[str, Any] = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._sg_from},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        if html:
            payload["content"].append({"type": "text/html", "value": html})
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {self._sg_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("EmailTool: sent via SendGrid to %s", to)
        return "sent:sendgrid"

    def _send_smtp(self, to: str, subject: str, body: str) -> str:
        msg = MIMEMultipart()
        msg["From"] = self._smtp_from or self._smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.starttls()
            if self._smtp_user:
                server.login(self._smtp_user, self._smtp_password)
            server.sendmail(msg["From"], to, msg.as_string())
        logger.info("EmailTool: sent via SMTP to %s", to)
        return "sent:smtp"

    def schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "to":      {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject."},
                    "body":    {"type": "string", "description": "Plain-text body."},
                    "html":    {"type": "string", "description": "Optional HTML body."},
                },
                "required": ["to", "subject", "body"],
            },
        }
