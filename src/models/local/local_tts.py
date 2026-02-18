"""Local text-to-speech using Piper TTS.

Provides offline TTS with voice models for multiple languages.
Voice models are stored in the configured piper_voices_dir.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import structlog

from src.models.protocols.voice import TTSResult
from src.utils.config import settings

logger = structlog.get_logger(__name__)

# Mapping from language code to Piper voice model name.
# These are the default voices; actual availability depends on downloaded models.
VOICE_MAP: dict[str, str] = {
    "en": "en_US-lessac-medium",
    "hi": "hi_IN-swara-medium",
    "es": "es_ES-sharvard-medium",
    "bn": "bn_BD-openjtalk-medium",
    "ta": "ta_IN-anbu-medium",
    "sw": "sw_KE-lanfrica-medium",
}

FALLBACK_VOICE = "en_US-lessac-medium"


class LocalTTS:
    """Piper TTS for local speech synthesis."""

    def __init__(self) -> None:
        self._voices_dir = Path(settings.voice.piper_voices_dir)
        logger.info("local_tts_initialized", voices_dir=str(self._voices_dir))

    def _get_voice_model(self, language: str) -> str:
        """Get the voice model name for a language, falling back to English."""
        voice = VOICE_MAP.get(language, FALLBACK_VOICE)

        # Check if model file exists locally
        model_path = self._voices_dir / f"{voice}.onnx"
        if not model_path.exists():
            logger.warning(
                "voice_model_not_found",
                language=language,
                voice=voice,
                fallback=FALLBACK_VOICE,
            )
            voice = FALLBACK_VOICE

        return voice

    async def synthesize(self, text: str, *, language: str = "en") -> TTSResult:
        """Synthesize text to speech audio (WAV format)."""
        t0 = time.monotonic()

        voice = self._get_voice_model(language)
        model_path = self._voices_dir / f"{voice}.onnx"
        config_path = self._voices_dir / f"{voice}.onnx.json"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
            out_path = out_f.name

        try:
            cmd = [
                "piper",
                "--model", str(model_path),
                "--output_file", out_path,
            ]
            if config_path.exists():
                cmd.extend(["--config", str(config_path)])

            proc = subprocess.run(  # noqa: S603
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=settings.voice.tts_timeout_seconds,
            )

            if proc.returncode != 0:
                logger.error(
                    "piper_tts_error",
                    returncode=proc.returncode,
                    stderr=proc.stderr.decode(errors="replace")[:500],
                )
                return TTSResult(audio_bytes=b"", format="wav", duration_ms=0)

            audio_bytes = Path(out_path).read_bytes()
        finally:
            Path(out_path).unlink(missing_ok=True)

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "local_tts_synthesize",
            language=language,
            voice=voice,
            audio_bytes=len(audio_bytes),
            latency_ms=elapsed,
        )

        return TTSResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_ms=elapsed,
        )
