"""Abstract base class for all OpenClaw agent tools."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseTool:
    """Abstract tool that agents can invoke during task execution.

    All tools must implement :meth:`execute`.  They can optionally override
    :meth:`validate` to check inputs before execution and :meth:`schema` to
    expose an OpenAI function-calling JSON Schema for LLM tool-use.
    """

    #: Human-readable name used in logs and the tool registry.
    name: str = "base_tool"
    #: One-sentence description shown to the LLM in function-calling mode.
    description: str = ""

    def execute(self, **kwargs: Any) -> Any:
        """Run the tool and return a result.

        Args:
            **kwargs: Tool-specific input parameters.

        Returns:
            Tool-specific output (any JSON-serialisable type).

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")

    def validate(self, **kwargs: Any) -> None:
        """Validate inputs before :meth:`execute` is called.

        Raises:
            ValueError: If any required argument is missing or invalid.
        """

    def schema(self) -> Dict[str, Any]:
        """Return an OpenAI function-calling JSON Schema for this tool.

        Override in subclasses to expose parameter types and descriptions.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    def __call__(self, **kwargs: Any) -> Any:
        self.validate(**kwargs)
        return self.execute(**kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
