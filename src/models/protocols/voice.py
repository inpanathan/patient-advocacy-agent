"""Protocol definitions for voice pipeline components.

Defines interfaces for STT, TTS, and language detection services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class STTResult:
    """Result from speech-to-text processing."""

    text: str
    language: str
    confidence: float
    duration_ms: int


@dataclass
class TTSResult:
    """Result from text-to-speech processing."""

    audio_bytes: bytes
    format: str  # "wav", "mp3", "opus"
    duration_ms: int


@dataclass
class LanguageDetectionResult:
    """Result from language detection."""

    language: str
    confidence: float
    alternatives: list[tuple[str, float]]


@runtime_checkable
class STTProtocol(Protocol):
    """Interface for speech-to-text services."""

    async def transcribe(self, audio_bytes: bytes, *, language_hint: str = "") -> STTResult:
        """Transcribe audio to text."""
        ...


@runtime_checkable
class TTSProtocol(Protocol):
    """Interface for text-to-speech services."""

    async def synthesize(self, text: str, *, language: str = "en") -> TTSResult:
        """Synthesize text to speech audio."""
        ...


@runtime_checkable
class LanguageDetectorProtocol(Protocol):
    """Interface for language detection."""

    async def detect(self, audio_bytes: bytes) -> LanguageDetectionResult:
        """Detect language from audio."""
        ...
