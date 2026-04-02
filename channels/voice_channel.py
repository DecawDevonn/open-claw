"""Voice channel adapter — transcribes audio and enqueues as text messages."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceChannel:
    """Adapter for voice / audio input.

    Accepts raw audio bytes or a URL pointing to an audio file, transcribes
    it via AssemblyAI (or any STT provider) and then enqueues the resulting
    text like any other message.

    Args:
        dispatcher:      A :class:`~gateway.dispatcher.Dispatcher` instance.
        assemblyai_key:  AssemblyAI API key.  Reads ``ASSEMBLYAI_API_KEY``
                         from the environment if not provided.
    """

    SOURCE = "voice"

    def __init__(self, dispatcher=None, assemblyai_key: str = "") -> None:
        import os
        self._dispatcher = dispatcher
        self._key = assemblyai_key or os.getenv("ASSEMBLYAI_API_KEY", "")

    async def handle_audio(
        self,
        session_id: str,
        audio_url: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
    ) -> Optional[str]:
        """Transcribe audio and enqueue the resulting text.

        Provide either *audio_url* or *audio_bytes* (not both).

        Args:
            session_id:  Identifier for the voice session / caller.
            audio_url:   Publicly accessible URL to an audio file.
            audio_bytes: Raw audio bytes (WAV, MP3, etc.).

        Returns:
            The transcribed text, or *None* if transcription failed.
        """
        if not audio_url and not audio_bytes:
            raise ValueError("VoiceChannel: provide either audio_url or audio_bytes")

        text = await self._transcribe(audio_url=audio_url, audio_bytes=audio_bytes)
        if not text:
            logger.warning("VoiceChannel: transcription returned empty text for session=%s", session_id)
            return None

        normalised = {
            "content": text,
            "session_id": session_id,
            "source": self.SOURCE,
        }

        if self._dispatcher is not None:
            await self._dispatcher.dispatch(normalised)
        else:
            logger.warning("VoiceChannel: no dispatcher — transcribed text dropped")

        return text

    async def _transcribe(
        self,
        audio_url: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
    ) -> Optional[str]:
        """Transcribe audio using the AssemblyAI REST API.

        Returns plain text, or *None* on error.
        """
        if not self._key:
            logger.error("VoiceChannel: ASSEMBLYAI_API_KEY not set — cannot transcribe")
            return None

        import asyncio
        import requests

        headers = {"authorization": self._key, "content-type": "application/json"}

        try:
            if audio_bytes:
                # Upload raw bytes first, then transcribe
                up = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": self._key},
                    data=audio_bytes,
                    timeout=30,
                )
                up.raise_for_status()
                audio_url = up.json()["upload_url"]

            resp = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                json={"audio_url": audio_url},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            transcript_id = resp.json()["id"]

            # Poll for completion (synchronous polling — replace with webhook in production)
            for _ in range(30):
                await asyncio.sleep(2)
                poll = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers,
                    timeout=10,
                )
                poll.raise_for_status()
                status = poll.json().get("status")
                if status == "completed":
                    return poll.json().get("text", "")
                if status == "error":
                    logger.error("VoiceChannel: AssemblyAI error: %s", poll.json().get("error"))
                    return None

            logger.warning("VoiceChannel: transcription timed out")
            return None

        except Exception as exc:
            logger.error("VoiceChannel: transcription exception: %s", exc)
            return None
