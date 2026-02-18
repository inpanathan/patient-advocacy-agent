"""Language detection service.

Detects the spoken language from audio input with confidence thresholds.
Supports minimum 5 languages for the Global South target populations.
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_voice import MockLanguageDetector
from src.models.protocols.voice import LanguageDetectorProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_language_detector() -> LanguageDetectorProtocol:
    """Factory to get the language detector based on model_backend setting."""
    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_language_detector")
        return MockLanguageDetector()

    if backend == "local":
        from src.models.local.local_language_detection import LocalLanguageDetector

        logger.info("using_local_language_detector")
        return LocalLanguageDetector()

    if backend == "cloud":
        from src.models.cloud.cloud_language_detection import CloudLanguageDetector

        logger.info("using_cloud_language_detector")
        return CloudLanguageDetector()

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
