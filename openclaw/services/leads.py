"""Lead management service.

Handles the full lead lifecycle for the Devonn.AI Multi-Channel Sales Brain:
  - Capture  : record inbound leads from any source (web form, social, ads)
  - Score    : AI-driven lead quality scoring and intent analysis
  - Route    : assign qualified leads to available agents
  - Follow-up: track interaction history and follow-up state

No external API dependencies; all persistence goes through the storage backend.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Numeric thresholds used by the rule-based fallback scorer
_HIGH_INTENT_KEYWORDS = {
    "buy", "purchase", "price", "cost", "quote", "demo", "trial", "sign up",
    "start", "ready", "now", "today", "urgent", "asap", "help",
}
_SOURCES_BY_QUALITY = {
    "ads": 20,
    "social": 15,
    "referral": 25,
    "website": 10,
    "organic": 10,
    "unknown": 5,
}


class LeadsService:
    """Manages leads stored in the application's storage backend."""

    def __init__(self, storage, ai_service=None) -> None:
        self._store = storage
        self._ai = ai_service

    # ── Capture ───────────────────────────────────────────────────────────────

    def capture(self, data: Dict[str, Any]) -> Dict:
        """Create and persist a new lead record.

        Required fields: ``name`` or ``email`` (at least one).
        Optional fields: ``phone``, ``source``, ``message``, ``company``,
        ``tags``, ``metadata``.
        """
        import uuid

        lead = {
            "id": str(uuid.uuid4()),
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "company": data.get("company", ""),
            "source": data.get("source", "unknown"),
            "message": data.get("message", ""),
            "tags": data.get("tags", []),
            "metadata": data.get("metadata", {}),
            "status": "new",
            "score": 0,
            "intent": "unknown",
            "assigned_agent": None,
            "follow_up_count": 0,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self._store.save_lead(lead)
        logger.info("Lead captured: %s", lead["id"])
        return lead

    # ── Score ─────────────────────────────────────────────────────────────────

    def score(self, lead_id: str) -> Dict:
        """Score a lead and update its record.

        Uses OpenAI when available; falls back to a deterministic rule-based
        scorer so the method always returns a valid result.
        """
        lead = self._store.get_lead(lead_id)
        if not lead:
            raise KeyError(f"Lead not found: {lead_id}")

        score, intent = self._compute_score(lead)
        lead["score"] = score
        lead["intent"] = intent
        lead["updated_at"] = _now()
        self._store.save_lead(lead)
        logger.info("Lead %s scored: %d (%s)", lead_id, score, intent)
        return lead

    def _compute_score(self, lead: Dict) -> tuple:
        """Return (score 0-100, intent label) for *lead*."""
        # Try AI scoring first
        if self._ai:
            try:
                return self._ai_score(lead)
            except Exception as exc:
                logger.warning("AI scoring failed, using fallback: %s", exc)

        # Rule-based fallback
        score = 0
        text = " ".join(
            [lead.get("message", ""), lead.get("name", ""), lead.get("company", "")]
        ).lower()

        # Source quality
        score += _SOURCES_BY_QUALITY.get(lead.get("source", "unknown"), 5)

        # Contact completeness
        if lead.get("email"):
            score += 15
        if lead.get("phone"):
            score += 15
        if lead.get("company"):
            score += 10

        # High-intent keyword detection
        keyword_hits = sum(1 for kw in _HIGH_INTENT_KEYWORDS if kw in text)
        score += min(keyword_hits * 5, 25)

        score = min(score, 100)
        intent = "high" if score >= 60 else "medium" if score >= 30 else "low"
        return score, intent

    def _ai_score(self, lead: Dict) -> tuple:
        """Delegate scoring to the AI service."""
        prompt = (
            "You are a lead-quality scorer for a B2B sales team. "
            "Given the following lead information, respond with a JSON object "
            "containing exactly two keys: 'score' (integer 0-100) and "
            "'intent' (one of: 'high', 'medium', 'low'). "
            "Respond ONLY with the JSON object, nothing else.\n\n"
            f"Name: {lead.get('name')}\n"
            f"Email: {lead.get('email')}\n"
            f"Company: {lead.get('company')}\n"
            f"Source: {lead.get('source')}\n"
            f"Message: {lead.get('message')}\n"
        )
        import json as _json
        raw = self._ai.complete(prompt, system="You are a lead scoring assistant.", max_tokens=64)
        parsed = _json.loads(raw)
        score = max(0, min(100, int(parsed.get("score", 0))))
        intent = parsed.get("intent", "low")
        if intent not in ("high", "medium", "low"):
            intent = "low"
        return score, intent

    # ── Route ─────────────────────────────────────────────────────────────────

    def route(self, lead_id: str) -> Dict:
        """Assign lead to the best available agent.

        Finds the agent with the fewest active tasks and an 'idle' or 'active'
        status.  If no agent is available the lead is marked 'unassigned'.
        """
        lead = self._store.get_lead(lead_id)
        if not lead:
            raise KeyError(f"Lead not found: {lead_id}")

        agents = self._store.list_agents()
        available = [a for a in agents if a.get("status") in ("idle", "active")]

        if available:
            # Pick agent with fewest assigned leads
            def _lead_count(agent):
                return sum(
                    1 for lead in self._store.list_leads()
                    if lead.get("assigned_agent") == agent["id"]
                )
            agent = min(available, key=_lead_count)
            lead["assigned_agent"] = agent["id"]
            lead["status"] = "assigned"
        else:
            lead["assigned_agent"] = None
            lead["status"] = "unassigned"

        lead["updated_at"] = _now()
        self._store.save_lead(lead)
        logger.info("Lead %s routed → agent %s", lead_id, lead["assigned_agent"])
        return lead

    # ── CRUD helpers ──────────────────────────────────────────────────────────

    def get(self, lead_id: str) -> Optional[Dict]:
        return self._store.get_lead(lead_id)

    def list(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict]:
        leads = self._store.list_leads()
        if status:
            leads = [lead for lead in leads if lead.get("status") == status]
        if source:
            leads = [lead for lead in leads if lead.get("source") == source]
        return leads

    def update(self, lead_id: str, data: Dict) -> Optional[Dict]:
        lead = self._store.get_lead(lead_id)
        if not lead:
            return None
        allowed = {"name", "email", "phone", "company", "source", "message",
                   "tags", "metadata", "status", "follow_up_count"}
        for key in allowed:
            if key in data:
                lead[key] = data[key]
        lead["updated_at"] = _now()
        self._store.save_lead(lead)
        return lead

    def delete(self, lead_id: str) -> bool:
        return self._store.delete_lead(lead_id)

    def record_follow_up(self, lead_id: str) -> Optional[Dict]:
        """Increment follow-up counter and timestamp."""
        lead = self._store.get_lead(lead_id)
        if not lead:
            return None
        lead["follow_up_count"] = lead.get("follow_up_count", 0) + 1
        lead["last_follow_up"] = _now()
        lead["updated_at"] = _now()
        self._store.save_lead(lead)
        return lead


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
