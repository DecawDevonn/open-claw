"""Task executor — runs an agent through a TaskPlan step by step."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .agent import Agent, AgentConfig
from .memory import AgentMemory
from .planner import MetaPlanner, TaskPlan
from .tools import ToolRegistry, get_default_registry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Outcome of a single framework execution run."""

    agent_id: str
    goal: str
    plan: Dict[str, Any]
    steps_completed: int
    output: Optional[Any] = None
    error: Optional[str] = None
    status: str = "done"              # done | error | partial
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None

    def finish(self, output: Any) -> "ExecutionResult":
        self.output = output
        self.finished_at = datetime.now(timezone.utc).isoformat()
        return self

    def fail(self, error: str) -> "ExecutionResult":
        self.error = error
        self.status = "error"
        self.finished_at = datetime.now(timezone.utc).isoformat()
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "goal": self.goal,
            "plan": self.plan,
            "steps_completed": self.steps_completed,
            "output": self.output,
            "error": self.error,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class TaskExecutor:
    """Executes a :class:`~openclaw.framework.planner.TaskPlan` using an agent.

    The executor is the heart of the OpenClaw framework.  It:

    1. Creates (or reuses) an :class:`Agent` from a config.
    2. Asks the :class:`MetaPlanner` to decompose the goal into steps.
    3. Iterates the steps, invoking tools via the :class:`ToolRegistry` and
       accumulating context in the agent's :class:`AgentMemory`.
    4. Returns an :class:`ExecutionResult` for the API layer.

    It is intentionally synchronous so it can be called from any Flask route
    without requiring a task queue.  Long-running executions should be
    dispatched via a background thread or Celery worker.
    """

    def __init__(
        self,
        ai_service: Optional[Any] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self._ai = ai_service
        self._registry = tool_registry or get_default_registry()
        self._planner = MetaPlanner(ai_service=ai_service)
        self._active: Dict[str, Agent] = {}

    # ── Public API ────────────────────────────────────────────────────────

    def spawn(self, config: AgentConfig) -> Agent:
        """Create and register a new agent instance."""
        agent = Agent(config)
        self._active[agent.id] = agent
        logger.info("Spawned agent %s (%s)", agent.id, config.name)
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._active.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._active.values()]

    def run(
        self,
        goal: str,
        agent_config: Optional[AgentConfig] = None,
        strategy: str = "sequential",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Spawn (or reuse) an agent and execute *goal*.

        Args:
            goal: The natural-language objective.
            agent_config: Agent configuration.  Defaults to a general-purpose
                executor if not supplied.
            strategy: ``'sequential'`` or ``'parallel'`` planning hint.
            context: Optional extra context passed to the planner.

        Returns:
            An :class:`ExecutionResult` describing the outcome.
        """
        if agent_config is None:
            agent_config = AgentConfig(name="openclaw-default", role="executor")

        agent = self.spawn(agent_config)
        memory = AgentMemory()
        plan = self._planner.plan(goal, strategy=strategy, context=context)

        result = ExecutionResult(
            agent_id=agent.id,
            goal=goal,
            plan=plan.to_dict(),
            steps_completed=0,
        )

        agent.start()
        agent.add_step("plan", plan.to_dict())

        try:
            output = self._execute_plan(agent, plan, memory, agent_config.max_steps)
            agent.finish(output)
            return result.finish(output)
        except Exception as exc:
            logger.exception("Agent %s failed: %s", agent.id, exc)
            agent.fail("Agent execution failed.")
            return result.fail("Agent execution failed.")

    # ── Internal execution loop ────────────────────────────────────────────

    def _execute_plan(
        self,
        agent: Agent,
        plan: TaskPlan,
        memory: AgentMemory,
        max_steps: int,
    ) -> Any:
        last_output: Any = None
        steps_run = 0

        for step in plan.steps:
            if steps_run >= max_steps:
                logger.warning("Agent %s hit max_steps=%d", agent.id, max_steps)
                break

            agent.add_step("step_start", step.to_dict())
            memory.remember("user", step.description)

            output = self._run_step(step, memory, agent.config)

            step.status = "done"
            step.output = output
            last_output = output
            steps_run += 1

            memory.remember("assistant", output)
            agent.add_step("step_done", {"step_id": step.id, "output": output})

        return last_output

    def _run_step(
        self,
        step: Any,
        memory: AgentMemory,
        config: AgentConfig,
    ) -> Any:
        """Execute one step — via tool if declared, via AI otherwise."""
        if step.tool and self._registry.get(step.tool):
            return self._registry.invoke(step.tool, query=step.description)

        if self._ai is not None:
            system = config.system_prompt or (
                f"You are {config.name}, a {config.role} agent. "
                "Complete the task accurately and concisely."
            )
            return self._ai.complete(
                prompt=step.description,
                system=system,
                temperature=config.temperature,
            )

        return f"[step: {step.description}]"
