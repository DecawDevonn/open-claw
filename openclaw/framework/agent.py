"""Agent class — represents a configured, runnable OpenClaw agent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentConfig:
    """Declarative configuration for a framework agent."""

    name: str
    role: str = "executor"
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    model: str = "gpt-4o"
    max_steps: int = 10
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        return cls(
            name=data["name"],
            role=data.get("role", "executor"),
            capabilities=data.get("capabilities", []),
            tools=data.get("tools", []),
            model=data.get("model", "gpt-4o"),
            max_steps=data.get("max_steps", 10),
            temperature=data.get("temperature", 0.7),
            system_prompt=data.get("system_prompt"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "model": self.model,
            "max_steps": self.max_steps,
            "temperature": self.temperature,
            "system_prompt": self.system_prompt,
            "metadata": self.metadata,
        }


class Agent:
    """A running OpenClaw agent instance.

    Wraps an :class:`AgentConfig` with runtime state (id, status, step log)
    so the executor can track progress and the API can report it.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.id: str = str(uuid.uuid4())
        self.config = config
        self.status: str = "idle"         # idle | running | done | error
        self.steps: List[Dict[str, Any]] = []
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.updated_at: str = self.created_at

    # ── Lifecycle helpers ──────────────────────────────────────────────────

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def start(self) -> None:
        self.status = "running"
        self._touch()

    def finish(self, result: Any) -> None:
        self.result = result
        self.status = "done"
        self._touch()

    def fail(self, error: str) -> None:
        self.error = error
        self.status = "error"
        self._touch()

    def add_step(self, step_type: str, content: Any) -> None:
        self.steps.append({
            "step": len(self.steps) + 1,
            "type": step_type,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._touch()

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config": self.config.to_dict(),
            "status": self.status,
            "steps": self.steps,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
