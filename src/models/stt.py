"""Speech-to-text service.

Provides STT with language detection, supporting 5+ languages.
Switches between mock, local (Faster-Whisper), and cloud (Google Cloud STT).
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockSTT
from src.models.protocols.voice import STTProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)

_instance: STTProtocol | None = None


def get_stt_service() -> STTProtocol:
    """Factory to get the STT service based on model_backend setting.

    Returns a singleton to avoid reloading the Whisper model on every request.
    """
    global _instance  # noqa: PLW0603
    if _instance is not None:
        return _instance

    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_stt")
        _instance = MockSTT()
        return _instance

    if backend == "local":
        try:
            from src.models.local.local_stt import LocalSTT

            logger.info("using_local_stt")
            _instance = LocalSTT()
            return _instance
        except ImportError as exc:
            logger.warning("local_stt_unavailable_falling_back_to_mock", error=str(exc))
            _instance = MockSTT()
            return _instance

    if backend == "cloud":
        from src.models.cloud.cloud_stt import CloudSTT

        logger.info("using_cloud_stt")
        _instance = CloudSTT()
        return _instance

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
