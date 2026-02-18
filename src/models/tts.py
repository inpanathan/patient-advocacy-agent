"""Text-to-speech service.

Provides TTS for patient explanations in detected language.
Switches between mock, local (Piper TTS), and cloud (Google Cloud TTS).
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockTTS
from src.models.protocols.voice import TTSProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_tts_service() -> TTSProtocol:
    """Factory to get the TTS service based on model_backend setting."""
    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_tts")
        return MockTTS()

    if backend == "local":
        from src.models.local.local_tts import LocalTTS

        logger.info("using_local_tts")
        return LocalTTS()

    if backend == "cloud":
        from src.models.cloud.cloud_tts import CloudTTS

        logger.info("using_cloud_tts")
        return CloudTTS()

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
