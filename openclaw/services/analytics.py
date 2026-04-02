"""Analytics & Optimization service.

Implements the Analytics & Optimization layer of the Devonn.AI system:
  - Event tracking   : record any interaction/conversion event
  - Metrics summary  : aggregate counts and rates over a time window
  - Feedback loops   : capture agent/task outcome signals for AI reinforcement

All data is persisted through the application's storage backend so it works
with both the in-memory store (tests / dev) and MongoDB (production).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Recognised event types — open set; unknown types are stored as-is.
KNOWN_EVENT_TYPES = {
    "lead_captured",
    "lead_scored",
    "lead_routed",
    "follow_up_sent",
    "call_initiated",
    "email_sent",
    "sms_sent",
    "whatsapp_sent",
    "payment_initiated",
    "payment_completed",
    "client_onboarded",
    "ad_click",
    "ad_conversion",
    "agent_assigned",
    "task_completed",
    "feedback_logged",
}


class AnalyticsService:
    """Tracks events and computes performance metrics for the sales pipeline."""

    def __init__(self, storage) -> None:
        self._store = storage

    # ── Event tracking ────────────────────────────────────────────────────────

    def track_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
    ) -> Dict:
        """Record an analytics event.

        Args:
            event_type: Semantic event name (e.g. ``"lead_captured"``).
            data:       Arbitrary payload attached to the event.
            actor_id:   User/agent that triggered the event (optional).

        Returns:
            The persisted event record.
        """
        import uuid

        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "data": data or {},
            "actor_id": actor_id,
            "timestamp": _now(),
        }
        self._store.save_event(event)
        logger.debug("Event tracked: %s (%s)", event_type, event["id"])
        return event

    # ── Metrics ───────────────────────────────────────────────────────────────

    def get_metrics(self, since: Optional[str] = None) -> Dict:
        """Return aggregated performance metrics.

        Args:
            since: ISO-8601 timestamp string; only events at or after this
                   time are included.  If omitted, all events are counted.

        Returns:
            Dict with ``total_events``, ``by_type`` counts, and derived
            KPIs such as ``conversion_rate`` and ``lead_to_close_rate``.
        """
        events = self._store.list_events()
        if since:
            events = [e for e in events if e.get("timestamp", "") >= since]

        by_type: Dict[str, int] = {}
        for ev in events:
            et = ev.get("event_type", "unknown")
            by_type[et] = by_type.get(et, 0) + 1

        captured = by_type.get("lead_captured", 0)
        closed = by_type.get("payment_completed", 0)
        onboarded = by_type.get("client_onboarded", 0)

        return {
            "total_events": len(events),
            "by_type": by_type,
            "leads_captured": captured,
            "payments_completed": closed,
            "clients_onboarded": onboarded,
            "conversion_rate": _safe_rate(closed, captured),
            "onboarding_rate": _safe_rate(onboarded, closed),
            "since": since,
            "computed_at": _now(),
        }

    # ── Feedback / Reinforcement loop ─────────────────────────────────────────

    def log_feedback(
        self,
        agent_id: str,
        task_id: str,
        outcome: str,
        score: float,
        notes: Optional[str] = None,
    ) -> Dict:
        """Record an AI feedback signal for reinforcement learning.

        Args:
            agent_id: Identifier of the agent that executed the task.
            task_id:  Identifier of the completed task.
            outcome:  ``"success"``, ``"failure"``, or ``"partial"``.
            score:    Numeric quality score 0.0–1.0.
            notes:    Free-text notes (optional).

        Returns:
            The persisted feedback record.
        """
        import uuid

        feedback = {
            "id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "task_id": task_id,
            "outcome": outcome,
            "score": max(0.0, min(1.0, float(score))),
            "notes": notes or "",
            "timestamp": _now(),
        }
        self._store.save_event({**feedback, "event_type": "feedback_logged"})
        logger.info("Feedback logged for agent %s / task %s: %s (%.2f)",
                    agent_id, task_id, outcome, score)
        return feedback

    def get_feedback_summary(self, agent_id: Optional[str] = None) -> Dict:
        """Summarise feedback signals, optionally filtered by agent.

        Returns:
            Dict with total count, outcome distribution, and mean score.
        """
        events = [
            e for e in self._store.list_events()
            if e.get("event_type") == "feedback_logged"
        ]
        if agent_id:
            events = [e for e in events if e.get("agent_id") == agent_id]

        outcomes: Dict[str, int] = {}
        scores: List[float] = []
        for ev in events:
            outcome = ev.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if "score" in ev:
                scores.append(float(ev["score"]))

        mean_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "total_feedback": len(events),
            "outcomes": outcomes,
            "mean_score": round(mean_score, 4),
            "agent_id": agent_id,
            "computed_at": _now(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
