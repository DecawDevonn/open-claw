"""OpenAI tool — wraps the OpenAI Chat Completions API as an agent tool."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class OpenAITool(BaseTool):
    """Calls the OpenAI Chat Completions API.

    Args:
        api_key:     OpenAI API key.  Falls back to ``OPENAI_API_KEY``.
        model:       Model name (default ``gpt-4o-mini``).
        system:      System prompt injected into every request.
        max_tokens:  Maximum completion tokens (default 512).
        temperature: Sampling temperature (default 0.7).
    """

    name: str = "openai_complete"
    description: str = "Generate a text completion using OpenAI Chat Completions."

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        system: str = "You are a helpful AI assistant.",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._system = system
        self._max_tokens = max_tokens
        self._temperature = temperature

    def validate(self, **kwargs: Any) -> None:
        if not kwargs.get("prompt"):
            raise ValueError("OpenAITool: 'prompt' is required")
        if not self._api_key:
            raise RuntimeError("OpenAITool: OPENAI_API_KEY is not configured")

    def execute(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        """Call the Chat Completions API and return the reply text.

        Args:
            prompt: User message to send.
            system: Optional override for the system prompt.

        Returns:
            The model's reply as a string.
        """
        import requests

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system or self._system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error("OpenAITool: API error: %s", exc)
            raise

    def schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user message to complete."},
                    "system": {"type": "string", "description": "Optional system prompt override."},
                },
                "required": ["prompt"],
            },
        }
