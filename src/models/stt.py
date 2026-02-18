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


def get_stt_service() -> STTProtocol:
    """Factory to get the STT service based on model_backend setting."""
    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_stt")
        return MockSTT()

    if backend == "local":
        from src.models.local.local_stt import LocalSTT

        logger.info("using_local_stt")
        return LocalSTT()

    if backend == "cloud":
        from src.models.cloud.cloud_stt import CloudSTT

        logger.info("using_cloud_stt")
        return CloudSTT()

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
