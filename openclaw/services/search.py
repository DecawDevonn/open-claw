"""Search / vector-DB service module.

Wraps:
  - Pinecone  (vector upsert, query, delete)
  - SerpAPI   (Google web search)
  - Algolia   (full-text / keyword search)
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_SERPAPI_BASE = "https://serpapi.com/search"
_ALGOLIA_BASE = "https://{app_id}.algolia.net/1"


class SearchService:
    """Unified interface for vector and keyword search providers."""

    def __init__(
        self,
        pinecone_api_key: Optional[str] = None,
        pinecone_environment: str = "us-east-1",
        pinecone_index: str = "openclaw",
        serpapi_key: Optional[str] = None,
        algolia_api_key: Optional[str] = None,
        algolia_app_id: Optional[str] = None,
    ) -> None:
        self._pc_key = pinecone_api_key
        self._pc_env = pinecone_environment
        self._pc_index = pinecone_index
        self._serp_key = serpapi_key
        self._algolia_key = algolia_api_key
        self._algolia_app_id = algolia_app_id

    # ── Pinecone helpers ──────────────────────────────────────────────────────

    @property
    def _pinecone_host(self) -> str:
        return f"https://{self._pc_index}-{self._pc_env}.svc.{self._pc_env}.pinecone.io"

    def _pc_headers(self) -> Dict[str, str]:
        if not self._pc_key:
            raise RuntimeError("PINECONE_API_KEY is not configured.")
        return {"Api-Key": self._pc_key, "Content-Type": "application/json"}

    # ── Pinecone — upsert ─────────────────────────────────────────────────────

    def vector_upsert(self, vectors: List[Dict[str, Any]], namespace: str = "") -> Dict:
        """Upsert a list of ``{id, values, metadata}`` dicts into Pinecone."""
        payload: Dict[str, Any] = {"vectors": vectors}
        if namespace:
            payload["namespace"] = namespace
        resp = requests.post(
            f"{self._pinecone_host}/vectors/upsert",
            headers=self._pc_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Pinecone — query ──────────────────────────────────────────────────────

    def vector_query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: str = "",
        include_metadata: bool = True,
        filter: Optional[Dict] = None,
    ) -> Dict:
        """Query Pinecone for nearest neighbours of *vector*."""
        payload: Dict[str, Any] = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": include_metadata,
        }
        if namespace:
            payload["namespace"] = namespace
        if filter:
            payload["filter"] = filter
        resp = requests.post(
            f"{self._pinecone_host}/query",
            headers=self._pc_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Pinecone — delete ─────────────────────────────────────────────────────

    def vector_delete(self, ids: List[str], namespace: str = "") -> Dict:
        """Delete vectors by ID from Pinecone."""
        payload: Dict[str, Any] = {"ids": ids}
        if namespace:
            payload["namespace"] = namespace
        resp = requests.post(
            f"{self._pinecone_host}/vectors/delete",
            headers=self._pc_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── SerpAPI — web search ──────────────────────────────────────────────────

    def web_search(self, query: str, num: int = 10, engine: str = "google") -> Dict:
        """Perform a web search via SerpAPI and return the raw result dict."""
        if not self._serp_key:
            raise RuntimeError("SERPAPI_KEY is not configured.")
        resp = requests.get(
            _SERPAPI_BASE,
            params={"q": query, "num": num, "engine": engine, "api_key": self._serp_key},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Algolia — search ──────────────────────────────────────────────────────

    def _algolia_headers(self) -> Dict[str, str]:
        if not self._algolia_key or not self._algolia_app_id:
            raise RuntimeError("ALGOLIA_API_KEY and ALGOLIA_APP_ID must both be configured.")
        return {
            "X-Algolia-API-Key": self._algolia_key,
            "X-Algolia-Application-Id": self._algolia_app_id,
            "Content-Type": "application/json",
        }

    def algolia_search(self, index: str, query: str, hits_per_page: int = 20) -> Dict:
        """Search an Algolia index and return the result dict."""
        base = _ALGOLIA_BASE.format(app_id=self._algolia_app_id)
        resp = requests.post(
            f"{base}/indexes/{index}/query",
            headers=self._algolia_headers(),
            json={"query": query, "hitsPerPage": hits_per_page},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
