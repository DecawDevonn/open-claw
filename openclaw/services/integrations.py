"""Integration relay service.

Wraps:
  - Generic outbound webhook relay (Pabbly Connect / n8n / Make.com)
  - Airtable  (create / list records)
  - Google Sheets  (append rows)

All methods use ``requests`` directly; no heavyweight SDK dependencies.
"""

import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_AIRTABLE_BASE = "https://api.airtable.com/v0"
_SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class IntegrationsService:
    """Outbound integration relay for automation and data platforms."""

    def __init__(
        self,
        webhook_secret_key: Optional[str] = None,
        pabbly_api_key: Optional[str] = None,
        airtable_api_key: Optional[str] = None,
        airtable_base_id: Optional[str] = None,
        google_sheets_api_key: Optional[str] = None,
    ) -> None:
        self._webhook_secret = webhook_secret_key
        self._pabbly_key = pabbly_api_key
        self._at_key = airtable_api_key
        self._at_base = airtable_base_id
        self._sheets_key = google_sheets_api_key

    # ── Webhook relay ─────────────────────────────────────────────────────────

    def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        sign: bool = True,
    ) -> Dict:
        """POST *payload* to *url*.

        When *sign* is True and ``WEBHOOK_SECRET_KEY`` is set, an
        HMAC-SHA256 signature is added as the ``X-Signature`` header so the
        receiver can verify authenticity.
        """
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if sign and self._webhook_secret:
            import json
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
            sig = hmac.new(
                self._webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            headers["X-Signature"] = f"sha256={sig}"
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

    # ── Airtable ──────────────────────────────────────────────────────────────

    def _at_headers(self) -> Dict[str, str]:
        if not self._at_key:
            raise RuntimeError("AIRTABLE_API_KEY is not configured.")
        return {"Authorization": f"Bearer {self._at_key}", "Content-Type": "application/json"}

    def airtable_list(self, table: str, max_records: int = 100) -> List[Dict]:
        """List records from an Airtable table."""
        if not self._at_base:
            raise RuntimeError("AIRTABLE_BASE_ID is not configured.")
        resp = requests.get(
            f"{_AIRTABLE_BASE}/{self._at_base}/{table}",
            headers=self._at_headers(),
            params={"maxRecords": max_records},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("records", [])

    def airtable_create(self, table: str, fields: Dict[str, Any]) -> Dict:
        """Create a single record in an Airtable table."""
        if not self._at_base:
            raise RuntimeError("AIRTABLE_BASE_ID is not configured.")
        resp = requests.post(
            f"{_AIRTABLE_BASE}/{self._at_base}/{table}",
            headers=self._at_headers(),
            json={"fields": fields},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Google Sheets ─────────────────────────────────────────────────────────

    def sheets_append(
        self,
        spreadsheet_id: str,
        range_: str,
        values: List[List[Any]],
    ) -> Dict:
        """Append *values* to a Google Sheet range (API key auth)."""
        if not self._sheets_key:
            raise RuntimeError("GOOGLE_SHEETS_API_KEY is not configured.")
        resp = requests.post(
            f"{_SHEETS_BASE}/{spreadsheet_id}/values/{range_}:append",
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
                "key": self._sheets_key,
            },
            json={"values": values},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Inbound webhook signature verification ────────────────────────────────

    def verify_webhook_signature(self, body: bytes, signature_header: str) -> bool:
        """Verify an inbound HMAC-SHA256 ``X-Signature`` header.

        Returns True if the signature is valid, False otherwise.
        Never raises — safe to call in a request guard.
        """
        if not self._webhook_secret:
            logger.warning("WEBHOOK_SECRET_KEY is not set; skipping signature verification.")
            return True  # permissive when no secret is configured
        try:
            expected = "sha256=" + hmac.new(
                self._webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception:
            return False
