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

_instance: TTSProtocol | None = None


def get_tts_service() -> TTSProtocol:
    """Factory to get the TTS service based on model_backend setting.

    Returns a singleton to avoid re-initializing on every request.
    """
    global _instance  # noqa: PLW0603
    if _instance is not None:
        return _instance

    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_tts")
        _instance = MockTTS()
        return _instance

    if backend == "local":
        try:
            from src.models.local.local_tts import LocalTTS

            logger.info("using_local_tts")
            _instance = LocalTTS()
            return _instance
        except ImportError as exc:
            logger.warning("local_tts_unavailable_falling_back_to_mock", error=str(exc))
            _instance = MockTTS()
            return _instance

    if backend == "cloud":
        from src.models.cloud.cloud_tts import CloudTTS

        logger.info("using_cloud_tts")
        _instance = CloudTTS()
        return _instance

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
