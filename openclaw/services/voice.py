"""Voice / speech service module.

Wraps:
  - ElevenLabs   (text-to-speech)
  - AssemblyAI   (speech-to-text / audio intelligence)

Both providers are accessed via their REST APIs using ``requests`` so this
module has no heavyweight SDK dependency.
"""

import logging
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
_ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"


class VoiceService:
    """Unified interface for TTS and STT providers."""

    def __init__(
        self,
        elevenlabs_api_key: Optional[str] = None,
        elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL",
        assemblyai_api_key: Optional[str] = None,
    ) -> None:
        self._el_key = elevenlabs_api_key
        self._el_voice = elevenlabs_voice_id
        self._aai_key = assemblyai_api_key

    # ── ElevenLabs — TTS ──────────────────────────────────────────────────────

    def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> bytes:
        """Convert *text* to speech and return raw MP3 bytes."""
        if not self._el_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured.")
        vid = voice_id or self._el_voice
        payload: Dict = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": stability, "similarity_boost": similarity_boost},
        }
        resp = requests.post(
            f"{_ELEVENLABS_BASE}/text-to-speech/{vid}",
            headers={
                "xi-api-key": self._el_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content

    def list_voices(self) -> list:
        """Return available ElevenLabs voices."""
        if not self._el_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured.")
        resp = requests.get(
            f"{_ELEVENLABS_BASE}/voices",
            headers={"xi-api-key": self._el_key},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])

    # ── AssemblyAI — STT ──────────────────────────────────────────────────────

    def _aai_headers(self) -> Dict[str, str]:
        if not self._aai_key:
            raise RuntimeError("ASSEMBLYAI_API_KEY is not configured.")
        return {"authorization": self._aai_key, "content-type": "application/json"}

    def transcribe_url(
        self,
        audio_url: str,
        speaker_labels: bool = False,
        sentiment_analysis: bool = False,
        auto_chapters: bool = False,
    ) -> Dict:
        """Submit an audio URL to AssemblyAI and poll until transcription is complete."""
        payload: Dict = {
            "audio_url": audio_url,
            "speaker_labels": speaker_labels,
            "sentiment_analysis": sentiment_analysis,
            "auto_chapters": auto_chapters,
        }
        # Submit
        resp = requests.post(
            f"{_ASSEMBLYAI_BASE}/transcript",
            headers=self._aai_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        transcript_id = resp.json()["id"]

        # Poll
        polling_url = f"{_ASSEMBLYAI_BASE}/transcript/{transcript_id}"
        for _ in range(120):  # max ~10 min
            poll = requests.get(polling_url, headers=self._aai_headers(), timeout=15)
            poll.raise_for_status()
            result = poll.json()
            status = result.get("status")
            if status == "completed":
                return result
            if status == "error":
                raise RuntimeError(f"AssemblyAI transcription error: {result.get('error')}")
            time.sleep(5)
        raise TimeoutError("AssemblyAI transcription timed out after 10 minutes.")

    def transcribe_bytes(self, audio_bytes: bytes, content_type: str = "audio/mpeg") -> Dict:
        """Upload raw audio bytes to AssemblyAI and transcribe."""
        if not self._aai_key:
            raise RuntimeError("ASSEMBLYAI_API_KEY is not configured.")
        # Upload
        upload_resp = requests.post(
            f"{_ASSEMBLYAI_BASE}/upload",
            headers={"authorization": self._aai_key, "content-type": content_type},
            data=audio_bytes,
            timeout=120,
        )
        upload_resp.raise_for_status()
        audio_url = upload_resp.json()["upload_url"]
        return self.transcribe_url(audio_url)
