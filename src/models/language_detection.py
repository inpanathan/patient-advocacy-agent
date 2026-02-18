"""Language detection service.

Detects the spoken language from audio input with confidence thresholds.
Supports minimum 5 languages for the Global South target populations.

TODO: Requires integration with real language detection API.
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockLanguageDetector
from src.models.protocols.voice import LanguageDetectorProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_language_detector() -> LanguageDetectorProtocol:
    """Factory to get the language detector."""
    if settings.use_mocks:
        logger.info("using_mock_language_detector")
        return MockLanguageDetector()

    # TODO: Real language detection implementation
    logger.warning("real_language_detector_not_available", fallback="mock")
    return MockLanguageDetector()
