"""Cloud speech-to-text using Google Cloud Speech-to-Text v2.

Provides high-quality STT with broad language support
via Google Cloud APIs.
"""

from __future__ import annotations

import time

import structlog
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from src.models.protocols.voice import STTResult
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class CloudSTT:
    """Google Cloud Speech-to-Text v2."""

    def __init__(self) -> None:
        project = settings.voice.google_cloud_project
        if not project:
            msg = (
                "VOICE__GOOGLE_CLOUD_PROJECT must be set for cloud STT. "
                "Set it in .env or environment variables."
            )
            raise ValueError(msg)

        self._client = SpeechClient()
        self._project = project
        self._recognizer = f"projects/{project}/locations/global/recognizers/_"
        logger.info("cloud_stt_initialized", project=project)

    async def transcribe(
        self, audio_bytes: bytes, *, language_hint: str = ""
    ) -> STTResult:
        """Transcribe audio bytes to text using Cloud STT."""
        t0 = time.monotonic()

        language_codes = [language_hint] if language_hint else ["en-US", "hi-IN", "es-ES"]

        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=language_codes,
            model="long",
        )

        request = cloud_speech.RecognizeRequest(
            recognizer=self._recognizer,
            config=config,
            content=audio_bytes,
        )

        response = self._client.recognize(request=request)

        text = ""
        detected_language = language_hint or "en"
        confidence = 0.0

        for result in response.results:
            if result.alternatives:
                best = result.alternatives[0]
                text += best.transcript
                confidence = max(confidence, best.confidence)
                if result.language_code:
                    detected_language = result.language_code[:2]

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "cloud_stt_transcribe",
            language=detected_language,
            confidence=confidence,
            text_len=len(text),
            latency_ms=elapsed,
        )

        return STTResult(
            text=text,
            language=detected_language,
            confidence=confidence,
            duration_ms=elapsed,
        )
