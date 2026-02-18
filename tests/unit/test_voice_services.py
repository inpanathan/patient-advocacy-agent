"""Tests for voice pipeline services (STT, TTS, language detection)."""

from __future__ import annotations

import pytest

from src.models.mocks.mock_voice import MockLanguageDetector, MockSTT, MockTTS


class TestMockSTT:
    """Test mock speech-to-text service."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_result(self):
        """Mock STT returns a transcription."""
        stt = MockSTT()
        result = await stt.transcribe(b"\x00" * 1000)
        assert result.text
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_transcribe_uses_language_hint(self):
        """Mock STT respects language hint."""
        stt = MockSTT()
        result = await stt.transcribe(b"\x00" * 1000, language_hint="hi")
        assert result.language == "hi"


class TestMockTTS:
    """Test mock text-to-speech service."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio(self):
        """Mock TTS returns audio bytes."""
        tts = MockTTS()
        result = await tts.synthesize("Hello patient")
        assert len(result.audio_bytes) > 0
        assert result.format == "wav"
        assert result.duration_ms > 0


class TestMockLanguageDetector:
    """Test mock language detection."""

    @pytest.mark.asyncio
    async def test_detect_returns_result(self):
        """Mock detector returns a language result."""
        detector = MockLanguageDetector()
        result = await detector.detect(b"\x00" * 1000)
        assert result.language
        assert result.confidence > 0
        assert len(result.alternatives) > 0
