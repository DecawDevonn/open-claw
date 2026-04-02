"""Communications service.

Wraps outbound messaging channels required by the Devonn.AI sales pipeline:
  - Twilio SMS / WhatsApp  (send_sms, send_whatsapp, make_call)
  - SendGrid Email         (send_email)

All methods raise ``RuntimeError`` when the required credentials are missing
so callers receive a clear error rather than a cryptic ``None`` dereference.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_TWILIO_BASE = "https://api.twilio.com/2010-04-01"
_SENDGRID_BASE = "https://api.sendgrid.com/v3"


class CommsService:
    """Unified outbound communications across SMS, WhatsApp, voice, and email."""

    def __init__(
        self,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_from_number: Optional[str] = None,
        twilio_whatsapp_from: Optional[str] = None,
        sendgrid_api_key: Optional[str] = None,
        sendgrid_from_email: Optional[str] = None,
    ) -> None:
        self._twilio_sid = twilio_account_sid
        self._twilio_token = twilio_auth_token
        self._twilio_from = twilio_from_number
        self._twilio_wa_from = twilio_whatsapp_from
        self._sg_key = sendgrid_api_key
        self._sg_from = sendgrid_from_email

    # ── Twilio helpers ────────────────────────────────────────────────────────

    def _twilio_auth(self):
        if not self._twilio_sid or not self._twilio_token:
            raise RuntimeError(
                "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required."
            )
        return (self._twilio_sid, self._twilio_token)

    def _messages_url(self) -> str:
        return f"{_TWILIO_BASE}/Accounts/{self._twilio_sid}/Messages.json"

    # ── SMS ───────────────────────────────────────────────────────────────────

    def send_sms(self, to: str, body: str) -> Dict:
        """Send an SMS via Twilio.

        Args:
            to:   Recipient phone number in E.164 format (+1XXXXXXXXXX).
            body: Message text (≤ 1600 characters).

        Returns:
            Twilio message resource dict.
        """
        if not self._twilio_from:
            raise RuntimeError("TWILIO_FROM_NUMBER is required to send SMS.")
        auth = self._twilio_auth()
        resp = requests.post(
            self._messages_url(),
            auth=auth,
            data={"From": self._twilio_from, "To": to, "Body": body},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── WhatsApp ──────────────────────────────────────────────────────────────

    def send_whatsapp(self, to: str, body: str) -> Dict:
        """Send a WhatsApp message via Twilio.

        Args:
            to:   Recipient WhatsApp number in E.164 format.
            body: Message text.

        Returns:
            Twilio message resource dict.
        """
        wa_from = self._twilio_wa_from or (
            f"whatsapp:{self._twilio_from}" if self._twilio_from else None
        )
        if not wa_from:
            raise RuntimeError(
                "TWILIO_WHATSAPP_FROM or TWILIO_FROM_NUMBER is required for WhatsApp."
            )
        auth = self._twilio_auth()
        wa_to = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        resp = requests.post(
            self._messages_url(),
            auth=auth,
            data={"From": wa_from, "To": wa_to, "Body": body},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Voice call ────────────────────────────────────────────────────────────

    def make_call(self, to: str, twiml_url: str) -> Dict:
        """Initiate an outbound voice call via Twilio.

        Args:
            to:        Recipient phone number in E.164 format.
            twiml_url: Publicly accessible URL returning TwiML instructions.

        Returns:
            Twilio call resource dict.
        """
        if not self._twilio_from:
            raise RuntimeError("TWILIO_FROM_NUMBER is required to make calls.")
        auth = self._twilio_auth()
        calls_url = f"{_TWILIO_BASE}/Accounts/{self._twilio_sid}/Calls.json"
        resp = requests.post(
            calls_url,
            auth=auth,
            data={"From": self._twilio_from, "To": to, "Url": twiml_url},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Email ─────────────────────────────────────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> Dict:
        """Send a transactional email via SendGrid.

        Args:
            to:         Recipient email address.
            subject:    Email subject line.
            html_body:  HTML content of the email.
            text_body:  Plain-text fallback (optional).
            from_email: Override sender email (falls back to config).
            from_name:  Sender display name (optional).

        Returns:
            ``{"status": 202, "message": "accepted"}`` on success.
        """
        if not self._sg_key:
            raise RuntimeError("SENDGRID_API_KEY is required to send email.")
        sender = from_email or self._sg_from
        if not sender:
            raise RuntimeError("SENDGRID_FROM_EMAIL is required to send email.")

        from_obj: Dict[str, Any] = {"email": sender}
        if from_name:
            from_obj["name"] = from_name

        content: List[Dict[str, str]] = [{"type": "text/html", "value": html_body}]
        if text_body:
            content.insert(0, {"type": "text/plain", "value": text_body})

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": from_obj,
            "subject": subject,
            "content": content,
        }
        resp = requests.post(
            f"{_SENDGRID_BASE}/mail/send",
            headers={
                "Authorization": f"Bearer {self._sg_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return {"status": resp.status_code, "message": "accepted"}
