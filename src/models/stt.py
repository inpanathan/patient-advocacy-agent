"""Speech-to-text service.

Provides STT with language detection, supporting 5+ languages.
Uses mock implementation in dev mode; real Google Cloud STT in production.

TODO: Requires GOOGLE_CLOUD_STT_KEY for real implementation.
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockSTT
from src.models.protocols.voice import STTProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_stt_service() -> STTProtocol:
    """Factory to get the STT service."""
    if settings.use_mocks:
        logger.info("using_mock_stt")
        return MockSTT()

    # TODO: Real Google Cloud STT implementation
    logger.warning("real_stt_not_available", fallback="mock")
    return MockSTT()
