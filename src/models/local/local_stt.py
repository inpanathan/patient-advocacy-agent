"""Local speech-to-text using Faster-Whisper.

Uses CTranslate2-optimized Whisper models for fast on-device
transcription with automatic language detection.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import structlog
from faster_whisper import WhisperModel

from src.models.protocols.voice import STTResult
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class LocalSTT:
    """Faster-Whisper based speech-to-text."""

    def __init__(self) -> None:
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

        logger.info(
            "loading_local_stt",
            model_size=model_size,
            device=device,
            compute_type=compute_type,
        )
        t0 = time.monotonic()

        try:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and device == "cuda":
                logger.warning("stt_cuda_oom_falling_back_to_cpu", error=str(exc))
                device = "cpu"
                compute_type = "int8"
                self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
            else:
                raise

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("local_stt_loaded", model_size=model_size, device=device, load_ms=elapsed)

    async def transcribe(self, audio_bytes: bytes, *, language_hint: str = "") -> STTResult:
        """Transcribe audio bytes to text."""
        t0 = time.monotonic()

        # Write audio to temp file (Faster-Whisper reads from file via FFmpeg)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            segments, info = self._model.transcribe(
                tmp_path,
                language=language_hint or None,
                beam_size=5,
            )

            text_parts: list[str] = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts)
            detected_language = info.language
            confidence = info.language_probability
        except Exception as exc:
            logger.warning("local_stt_decode_error", error=str(exc), audio_bytes=len(audio_bytes))
            Path(tmp_path).unlink(missing_ok=True)
            return STTResult(text="", language=language_hint or "en", confidence=0.0, duration_ms=0)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "local_stt_transcribe",
            language=detected_language,
            confidence=confidence,
            text_len=len(text),
            latency_ms=elapsed,
        )

        return STTResult(
            text=text,
            language=detected_language,
            confidence=confidence,
            duration_ms=elapsed,
        )
