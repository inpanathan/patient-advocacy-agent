"""Cloud text-to-speech using Google Cloud Text-to-Speech.

Provides high-quality TTS with broad language and voice support
via Google Cloud APIs.
"""

from __future__ import annotations

import time

import structlog
from google.cloud import texttospeech

from src.models.protocols.voice import TTSResult

logger = structlog.get_logger(__name__)

# Mapping from language code to Google Cloud TTS voice config
VOICE_MAP: dict[str, tuple[str, str]] = {
    "en": ("en-US", "en-US-Neural2-D"),
    "hi": ("hi-IN", "hi-IN-Neural2-A"),
    "es": ("es-ES", "es-ES-Neural2-A"),
    "bn": ("bn-IN", "bn-IN-Standard-A"),
    "ta": ("ta-IN", "ta-IN-Standard-A"),
    "sw": ("sw-KE", "sw-KE-Standard-A"),
}

FALLBACK_LANG = "en"


class CloudTTS:
    """Google Cloud Text-to-Speech."""

    def __init__(self) -> None:
        self._client = texttospeech.TextToSpeechClient()
        logger.info("cloud_tts_initialized")

    async def synthesize(self, text: str, *, language: str = "en") -> TTSResult:
        """Synthesize text to speech audio (WAV format)."""
        t0 = time.monotonic()

        lang_code, voice_name = VOICE_MAP.get(
            language, VOICE_MAP[FALLBACK_LANG]
        )

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )

        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_bytes = response.audio_content
        elapsed = int((time.monotonic() - t0) * 1000)

        logger.info(
            "cloud_tts_synthesize",
            language=language,
            voice=voice_name,
            audio_bytes=len(audio_bytes),
            latency_ms=elapsed,
        )

        return TTSResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_ms=elapsed,
        )
