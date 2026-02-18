"""Local language detection using Faster-Whisper.

Leverages Whisper's built-in language detection to identify
the spoken language from audio samples.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import structlog
from faster_whisper import WhisperModel

from src.models.protocols.voice import LanguageDetectionResult
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class LocalLanguageDetector:
    """Faster-Whisper based language detection."""

    def __init__(self, whisper_model: WhisperModel | None = None) -> None:
        """Initialize with an optional shared Whisper model instance.

        Args:
            whisper_model: Existing WhisperModel to reuse. If None, loads a new one.
        """
        if whisper_model is not None:
            self._model = whisper_model
            logger.info("local_language_detector_shared_model")
        else:
            model_size = settings.voice.whisper_model_size
            device = "cuda"
            compute_type = "float16"

            try:
                import torch

                if not torch.cuda.is_available():
                    device = "cpu"
                    compute_type = "int8"
            except ImportError:
                device = "cpu"
                compute_type = "int8"

            logger.info("loading_local_language_detector", model_size=model_size)
            self._model = WhisperModel(
                model_size, device=device, compute_type=compute_type
            )
            logger.info("local_language_detector_loaded")

    async def detect(self, audio_bytes: bytes) -> LanguageDetectionResult:
        """Detect language from audio bytes."""
        t0 = time.monotonic()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            _segments, info = self._model.transcribe(
                tmp_path,
                language=None,  # auto-detect
                beam_size=1,  # fast pass for detection
            )
            # Force evaluation of the generator to populate info
            for _ in _segments:
                break

            detected_language = info.language
            confidence = info.language_probability
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Build alternatives list — Whisper only gives the top-1 natively,
        # so we return it as the sole entry with full confidence
        alternatives: list[tuple[str, float]] = [(detected_language, confidence)]

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "local_language_detect",
            language=detected_language,
            confidence=confidence,
            latency_ms=elapsed,
        )

        return LanguageDetectionResult(
            language=detected_language,
            confidence=confidence,
            alternatives=alternatives,
        )
