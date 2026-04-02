"""Tool registry — register and invoke agent tools."""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, List, Optional


class ToolSpec:
    """Descriptor for a single registered tool."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.fn = fn
        self.description = description
        self.parameters: Dict[str, Any] = parameters or {}

    def invoke(self, **kwargs: Any) -> Any:
        return self.fn(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Global registry that maps tool names to :class:`ToolSpec` instances.

    Agents declare which tools they need by name; the executor looks them up
    here at runtime.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> "ToolRegistry":
        self._tools[name] = ToolSpec(name, fn, description, parameters)
        return self

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def invoke(self, name: str, **kwargs: Any) -> Any:
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(f"Tool '{name}' not registered in the ToolRegistry.")
        return spec.invoke(**kwargs)

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def list_tools(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._tools.values()]


# ── Module-level default registry ──────────────────────────────────────────

_default_registry = ToolRegistry()


def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that registers a function as a tool in the default registry.

    Usage::

        @tool(name="web_search", description="Search the web")
        def web_search(query: str) -> str:
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or fn.__name__
        _default_registry.register(tool_name, fn, description, parameters)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_default_registry() -> ToolRegistry:
    return _default_registry


# ── Sapphire save_to_memory tool ──────────────────────────────────────────────

_SAVE_TO_MEMORY_PARAMS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The memory to store (a clear, self-contained statement).",
        },
        "weight": {
            "type": "number",
            "description": "Importance score 0.0–2.0 (default 1.0).",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional categorisation tags.",
        },
    },
    "required": ["content"],
}


def register_save_to_memory(memory_service: Any) -> None:
    """Register the ``save_to_memory`` tool against *memory_service*.

    Call this once after creating a :class:`~openclaw.services.sapphire.SapphireMemory`
    instance so agents can call ``save_to_memory`` by name.
    """

    def _save_to_memory(content: str, weight: float = 1.0, tags: Optional[List[str]] = None, **_: Any) -> str:
        mid = memory_service.save(content=content, weight=weight, tags=tags or [])
        return f"Memory saved: {mid}"

    _default_registry.register(
        name="save_to_memory",
        fn=_save_to_memory,
        description=(
            "Persist an important fact, insight, or piece of context to the "
            "Sapphire long-term memory store."
        ),
        parameters=_SAVE_TO_MEMORY_PARAMS,
    )
