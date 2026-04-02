"""Meta-planner — decomposes high-level goals into structured task plans."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TaskStep:
    """One step within a :class:`TaskPlan`."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    tool: Optional[str] = None           # tool name to invoke, if any
    depends_on: List[str] = field(default_factory=list)  # step ids
    status: str = "pending"              # pending | done | skip
    output: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "depends_on": self.depends_on,
            "status": self.status,
            "output": self.output,
        }


@dataclass
class TaskPlan:
    """A structured decomposition of a goal into ordered steps."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    strategy: str = "sequential"         # sequential | parallel
    steps: List[TaskStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_step(
        self,
        description: str,
        tool: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
    ) -> TaskStep:
        step = TaskStep(
            description=description,
            tool=tool,
            depends_on=depends_on or [],
        )
        self.steps.append(step)
        return step

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "strategy": self.strategy,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
        }


class MetaPlanner:
    """Decomposes an objective into a :class:`TaskPlan`.

    The default implementation does rule-based decomposition.  When an
    :class:`~openclaw.services.ai.AIService` instance is provided the planner
    can optionally use the LLM to produce richer plans.
    """

    def __init__(self, ai_service: Optional[Any] = None) -> None:
        self._ai = ai_service

    def plan(
        self,
        goal: str,
        strategy: str = "sequential",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskPlan:
        """Return a :class:`TaskPlan` for *goal*.

        If an AI service is available the planner asks the LLM for a JSON
        step list; otherwise it falls back to a single-step plan so the
        executor always has something to run.
        """
        task_plan = TaskPlan(goal=goal, strategy=strategy)

        if self._ai is not None:
            try:
                return self._ai_plan(task_plan, context or {})
            except Exception:
                pass  # fall through to default plan

        task_plan.add_step(description=goal)
        return task_plan

    # ── AI-assisted planning ───────────────────────────────────────────────

    def _ai_plan(self, plan: TaskPlan, context: Dict[str, Any]) -> TaskPlan:
        """Use the AI service to decompose the goal into steps."""
        system = (
            "You are a task planner. Given a goal, respond with a JSON array "
            "of step objects. Each step has keys: description (str), "
            "tool (str or null). Return ONLY the JSON array, no prose."
        )
        prompt = f"Goal: {plan.goal}\nContext: {context}"
        response = self._ai.complete(prompt=prompt, system=system, max_tokens=512)

        import json  # local import — only needed on this path

        raw = response if isinstance(response, str) else str(response)
        # Strip markdown fences if present
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        steps = json.loads(raw)
        for s in steps:
            plan.add_step(
                description=s.get("description", ""),
                tool=s.get("tool"),
            )
        return plan
