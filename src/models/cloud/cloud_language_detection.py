"""Cloud language detection using Google Cloud Speech-to-Text.

Uses Cloud STT's auto-detection capability to identify the
spoken language from audio samples.
"""

from __future__ import annotations

import time

import structlog
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from src.models.protocols.voice import LanguageDetectionResult
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class CloudLanguageDetector:
    """Google Cloud STT-based language detection."""

    def __init__(self) -> None:
        project = settings.voice.google_cloud_project
        if not project:
            msg = (
                "VOICE__GOOGLE_CLOUD_PROJECT must be set for cloud language detection. "
                "Set it in .env or environment variables."
            )
            raise ValueError(msg)

        self._client = SpeechClient()
        self._project = project
        self._recognizer = f"projects/{project}/locations/global/recognizers/_"
        logger.info("cloud_language_detector_initialized", project=project)

    async def detect(self, audio_bytes: bytes) -> LanguageDetectionResult:
        """Detect language from audio bytes using Cloud STT auto-detection."""
        t0 = time.monotonic()

        # Send with multiple language codes; Cloud STT will pick the best match
        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=["en-US", "hi-IN", "es-ES", "bn-IN", "ta-IN", "sw-KE"],
            model="long",
        )

        request = cloud_speech.RecognizeRequest(
            recognizer=self._recognizer,
            config=config,
            content=audio_bytes,
        )

        response = self._client.recognize(request=request)

        detected_language = "en"
        confidence = 0.0
        alternatives: list[tuple[str, float]] = []

        for result in response.results:
            if result.language_code:
                lang = result.language_code[:2]
                conf = result.alternatives[0].confidence if result.alternatives else 0.0
                if conf > confidence:
                    detected_language = lang
                    confidence = conf
                alternatives.append((lang, conf))

        if not alternatives:
            alternatives = [(detected_language, confidence)]

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "cloud_language_detect",
            language=detected_language,
            confidence=confidence,
            latency_ms=elapsed,
        )

        return LanguageDetectionResult(
            language=detected_language,
            confidence=confidence,
            alternatives=alternatives,
        )
