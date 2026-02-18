"""Text-to-speech service.

Provides TTS for patient explanations in detected language.
Uses mock implementation in dev mode; real Google Cloud TTS in production.

TODO: Requires GOOGLE_CLOUD_TTS_KEY for real implementation.
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockTTS
from src.models.protocols.voice import TTSProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_tts_service() -> TTSProtocol:
    """Factory to get the TTS service."""
    if settings.use_mocks:
        logger.info("using_mock_tts")
        return MockTTS()

    # TODO: Real Google Cloud TTS implementation
    logger.warning("real_tts_not_available", fallback="mock")
    return MockTTS()
