"""Embeddings helper — generate and cache text embeddings.

The default provider is OpenAI's ``text-embedding-3-small`` model.  Swap
in any other embedding provider by subclassing :class:`EmbeddingsProvider`.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EmbeddingsProvider:
    """Abstract base for embedding providers.

    Subclass and override :meth:`embed` to use a different backend
    (HuggingFace, Cohere, local sentence-transformers, etc.).
    """

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class OpenAIEmbeddings(EmbeddingsProvider):
    """Generate embeddings using the OpenAI Embeddings API.

    Args:
        api_key: OpenAI API key.  Falls back to ``OPENAI_API_KEY``.
        model:   Embedding model name (default ``text-embedding-3-small``).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._cache: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        """Return the embedding vector for *text*.

        Results are cached in-process by exact text match.

        Args:
            text: Input string to embed.

        Returns:
            Float list (embedding vector).
        """
        if not self._api_key:
            raise RuntimeError("OpenAIEmbeddings: OPENAI_API_KEY is not configured")

        if text in self._cache:
            return self._cache[text]

        import requests

        resp = requests.post(
            "https://api.openai.com/v1/embeddings",
            json={"input": text, "model": self._model},
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        resp.raise_for_status()
        vector = resp.json()["data"][0]["embedding"]
        self._cache[text] = vector
        return vector

    def cache_size(self) -> int:
        """Return the number of cached embeddings."""
        return len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()
