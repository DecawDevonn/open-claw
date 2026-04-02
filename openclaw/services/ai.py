"""AI / NLP service module.

Wraps:
  - OpenAI  (text completion, embeddings, image generation, Whisper transcription)
  - HuggingFace Inference API  (custom NLP models)
  - StabilityAI  (image generation fallback)
  - DeepL  (translation)

Every method raises ``RuntimeError`` when the required API key is missing so
callers receive a clear message rather than a cryptic ``None`` dereference.
All external I/O is isolated in this module so tests can patch ``requests`` or
the OpenAI client in one place.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_OPENAI_BASE = "https://api.openai.com/v1"
_HF_BASE = "https://api-inference.huggingface.co/models"
_STABILITY_BASE = "https://api.stability.ai/v1"
_DEEPL_BASE = "https://api-free.deepl.com/v2"


class AIService:
    """Unified interface to all AI / NLP providers."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini",
        openai_embedding_model: str = "text-embedding-3-small",
        hf_api_token: Optional[str] = None,
        hf_model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        stability_api_key: Optional[str] = None,
        deepl_api_key: Optional[str] = None,
    ) -> None:
        self._openai_key = openai_api_key
        self._openai_model = openai_model
        self._openai_embed_model = openai_embedding_model
        self._hf_token = hf_api_token
        self._hf_model = hf_model
        self._stability_key = stability_api_key
        self._deepl_key = deepl_api_key

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _openai_headers(self) -> Dict[str, str]:
        if not self._openai_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        return {"Authorization": f"Bearer {self._openai_key}", "Content-Type": "application/json"}

    def _hf_headers(self) -> Dict[str, str]:
        if not self._hf_token:
            raise RuntimeError("HF_API_TOKEN is not configured.")
        return {"Authorization": f"Bearer {self._hf_token}"}

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> Dict:
        resp.raise_for_status()
        return resp.json()

    # ── OpenAI — text completion ──────────────────────────────────────────────

    def complete(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> str:
        """Send a chat completion request and return the assistant reply."""
        payload: Dict[str, Any] = {
            "model": model or self._openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = self._raise_for_status(
            requests.post(
                f"{_OPENAI_BASE}/chat/completions",
                headers=self._openai_headers(),
                json=payload,
                timeout=60,
            )
        )
        return data["choices"][0]["message"]["content"]

    # ── OpenAI — embeddings ───────────────────────────────────────────────────

    def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """Return an embedding vector for *text*."""
        data = self._raise_for_status(
            requests.post(
                f"{_OPENAI_BASE}/embeddings",
                headers=self._openai_headers(),
                json={"model": model or self._openai_embed_model, "input": text},
                timeout=30,
            )
        )
        return data["data"][0]["embedding"]

    # ── OpenAI — image generation ─────────────────────────────────────────────

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        model: str = "dall-e-3",
    ) -> List[str]:
        """Generate images and return a list of URLs."""
        data = self._raise_for_status(
            requests.post(
                f"{_OPENAI_BASE}/images/generations",
                headers=self._openai_headers(),
                json={"model": model, "prompt": prompt, "n": n, "size": size},
                timeout=60,
            )
        )
        return [item["url"] for item in data["data"]]

    # ── OpenAI Whisper — transcription ────────────────────────────────────────

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> str:
        """Transcribe audio using Whisper and return the transcript text."""
        if not self._openai_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        resp = requests.post(
            f"{_OPENAI_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {self._openai_key}"},
            files={"file": (filename, audio_bytes, "audio/mpeg")},
            data={"model": "whisper-1"},
            timeout=120,
        )
        return self._raise_for_status(resp)["text"]

    # ── HuggingFace — inference ───────────────────────────────────────────────

    def hf_infer(self, text: str, model: Optional[str] = None) -> Any:
        """Run inference against a HuggingFace model and return raw output."""
        url = f"{_HF_BASE}/{model or self._hf_model}"
        data = self._raise_for_status(
            requests.post(
                url,
                headers=self._hf_headers(),
                json={"inputs": text},
                timeout=60,
            )
        )
        return data

    # ── StabilityAI — image generation ───────────────────────────────────────

    def stability_generate(
        self,
        prompt: str,
        engine: str = "stable-diffusion-xl-1024-v1-0",
        steps: int = 30,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
    ) -> List[str]:
        """Generate images via StabilityAI and return base64-encoded strings."""
        if not self._stability_key:
            raise RuntimeError("STABILITY_API_KEY is not configured.")
        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": cfg_scale,
            "steps": steps,
            "width": width,
            "height": height,
        }
        data = self._raise_for_status(
            requests.post(
                f"{_STABILITY_BASE}/generation/{engine}/text-to-image",
                headers={
                    "Authorization": f"Bearer {self._stability_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=120,
            )
        )
        return [artifact["base64"] for artifact in data.get("artifacts", [])]

    # ── DeepL — translation ───────────────────────────────────────────────────

    def translate(self, text: str, target_lang: str = "EN-US", source_lang: Optional[str] = None) -> str:
        """Translate *text* with DeepL and return the translated string."""
        if not self._deepl_key:
            raise RuntimeError("DEEPL_API_KEY is not configured.")
        payload: Dict[str, Any] = {"text": [text], "target_lang": target_lang}
        if source_lang:
            payload["source_lang"] = source_lang
        data = self._raise_for_status(
            requests.post(
                f"{_DEEPL_BASE}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self._deepl_key}"},
                json=payload,
                timeout=30,
            )
        )
        return data["translations"][0]["text"]
