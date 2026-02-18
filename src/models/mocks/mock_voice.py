"""Mock voice pipeline components for development and testing.

Provides mock STT, TTS, and language detection that return
realistic test data without requiring external services.
"""

from __future__ import annotations

import structlog

from src.models.protocols.voice import (
    LanguageDetectionResult,
    STTResult,
    TTSResult,
)

logger = structlog.get_logger(__name__)


class MockSTT:
    """Mock speech-to-text service."""

    def __init__(self) -> None:
        logger.info("mock_stt_loaded")

    async def transcribe(self, audio_bytes: bytes, *, language_hint: str = "") -> STTResult:
        """Return a mock transcription."""
        lang = language_hint or "en"
        return STTResult(
            text="I have a rash on my arm that has been itching for three days.",
            language=lang,
            confidence=0.95,
            duration_ms=len(audio_bytes) // 16,  # rough estimate
        )


class MockTTS:
    """Mock text-to-speech service."""

    def __init__(self) -> None:
        logger.info("mock_tts_loaded")

    async def synthesize(self, text: str, *, language: str = "en") -> TTSResult:
        """Return mock audio bytes."""
        mock_audio = b"\x00" * (len(text) * 100)  # proportional to text length
        return TTSResult(
            audio_bytes=mock_audio,
            format="wav",
            duration_ms=len(text) * 50,
        )


class MockLanguageDetector:
    """Mock language detection service."""

    def __init__(self) -> None:
        logger.info("mock_language_detector_loaded")

    async def detect(self, audio_bytes: bytes) -> LanguageDetectionResult:
        """Return a mock language detection result."""
        return LanguageDetectionResult(
            language="hi",
            confidence=0.92,
            alternatives=[("hi", 0.92), ("bn", 0.05), ("ta", 0.03)],
        )
