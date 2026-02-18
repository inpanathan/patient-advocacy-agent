"""Integration tests for local model implementations.

These tests require MODEL_BACKEND=local and actual model weights.
They are skipped when running in mock mode (the default).

Run with:
    MODEL_BACKEND=local uv run pytest tests/integration/test_local_models.py -v
"""

from __future__ import annotations

import os

import pytest

# Skip entire module unless MODEL_BACKEND=local
pytestmark = pytest.mark.skipif(
    os.environ.get("MODEL_BACKEND", "mock") != "local",
    reason="Requires MODEL_BACKEND=local and downloaded model weights",
)


# ---------------------------------------------------------------------------
# Medical model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_medical_generate() -> None:
    """Load LocalMedicalModel and generate a basic response."""
    from src.models.local.local_medical import LocalMedicalModel
    from src.models.protocols.medical import MedicalModelResponse

    model = LocalMedicalModel()
    response = await model.generate("What are common causes of skin rashes?")

    assert isinstance(response, MedicalModelResponse)
    assert len(response.text) > 0
    assert response.model_id != ""
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.latency_ms > 0


@pytest.mark.asyncio
async def test_local_medical_soap() -> None:
    """Generate a SOAP note and verify all sections are populated."""
    from src.models.local.local_medical import LocalMedicalModel
    from src.models.protocols.medical import SOAPNote

    model = LocalMedicalModel()
    soap = await model.generate_soap(
        transcript="Patient reports a red, itchy rash on both arms for 5 days.",
        image_context="Erythematous patches with mild scaling visible on forearms.",
        rag_context="Similar cases suggest atopic dermatitis (L20.0).",
    )

    assert isinstance(soap, SOAPNote)
    assert len(soap.subjective) > 0
    assert soap.disclaimer != ""


# ---------------------------------------------------------------------------
# Embedding model tests
# ---------------------------------------------------------------------------


def test_local_embedding_text() -> None:
    """Embed text and verify dimension and normalization."""
    import numpy as np

    from src.models.local.local_embedding import LocalEmbeddingModel

    model = LocalEmbeddingModel()
    embedding = model.embed_text("red itchy rash on arm")

    assert embedding.shape == (model.dimension,)
    norm = float(np.linalg.norm(embedding))
    assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


def test_local_embedding_image(tmp_path: pytest.TempPathFactory) -> None:
    """Embed a test image and verify dimension and normalization."""
    import numpy as np
    from PIL import Image

    from src.models.local.local_embedding import LocalEmbeddingModel

    # Create a simple test image
    img = Image.new("RGB", (384, 384), color=(200, 100, 100))
    img_path = str(tmp_path / "test_skin.png")  # type: ignore[operator]
    img.save(img_path)

    model = LocalEmbeddingModel()
    embedding = model.embed_image(img_path)

    assert embedding.shape == (model.dimension,)
    norm = float(np.linalg.norm(embedding))
    assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


def test_local_embedding_similarity(tmp_path: pytest.TempPathFactory) -> None:
    """Verify that related text/image pairs have higher similarity."""
    import numpy as np
    from PIL import Image

    from src.models.local.local_embedding import LocalEmbeddingModel

    model = LocalEmbeddingModel()

    # Text embeddings
    emb_rash = model.embed_text("red itchy skin rash dermatitis")
    emb_unrelated = model.embed_text("quantum physics particle accelerator")

    # Image embedding (a reddish image)
    img = Image.new("RGB", (384, 384), color=(200, 50, 50))
    img_path = str(tmp_path / "rash.png")  # type: ignore[operator]
    img.save(img_path)
    emb_img = model.embed_image(img_path)

    # Related text should be more similar to the reddish image than unrelated text
    sim_related = float(np.dot(emb_rash, emb_img))
    sim_unrelated = float(np.dot(emb_unrelated, emb_img))

    assert sim_related > sim_unrelated, (
        f"Expected related similarity ({sim_related:.4f}) > "
        f"unrelated ({sim_unrelated:.4f})"
    )


# ---------------------------------------------------------------------------
# STT tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_stt_transcribe() -> None:
    """Transcribe sample audio and verify STTResult structure."""
    from src.models.local.local_stt import LocalSTT
    from src.models.protocols.voice import STTResult

    stt = LocalSTT()

    # Create minimal WAV header + silence (1 second of 16kHz mono 16-bit)
    import struct

    sample_rate = 16000
    num_samples = sample_rate  # 1 second
    data_size = num_samples * 2  # 16-bit = 2 bytes
    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,  # chunk size
        1,  # PCM
        1,  # mono
        sample_rate,
        sample_rate * 2,  # byte rate
        2,  # block align
        16,  # bits per sample
        b"data",
        data_size,
    )
    audio_bytes = wav_header + b"\x00" * data_size

    result = await stt.transcribe(audio_bytes)

    assert isinstance(result, STTResult)
    assert isinstance(result.text, str)
    assert isinstance(result.language, str)
    assert result.duration_ms > 0


# ---------------------------------------------------------------------------
# TTS tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_tts_synthesize() -> None:
    """Synthesize text and verify TTSResult structure."""
    from src.models.local.local_tts import LocalTTS
    from src.models.protocols.voice import TTSResult

    tts = LocalTTS()
    result = await tts.synthesize("Hello, how are you feeling today?", language="en")

    assert isinstance(result, TTSResult)
    assert result.format == "wav"
    # Audio bytes may be empty if Piper voice model not installed
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_language_detection() -> None:
    """Detect language from audio and verify result structure."""
    import struct

    from src.models.local.local_language_detection import LocalLanguageDetector
    from src.models.protocols.voice import LanguageDetectionResult

    detector = LocalLanguageDetector()

    # Create minimal WAV with silence
    sample_rate = 16000
    num_samples = sample_rate
    data_size = num_samples * 2
    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    audio_bytes = wav_header + b"\x00" * data_size

    result = await detector.detect(audio_bytes)

    assert isinstance(result, LanguageDetectionResult)
    assert isinstance(result.language, str)
    assert len(result.alternatives) > 0


# ---------------------------------------------------------------------------
# Full pipeline test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_full_pipeline() -> None:
    """End-to-end: STT → medical model → SOAP note with real models."""
    from src.models.local.local_medical import LocalMedicalModel
    from src.models.protocols.medical import SOAPNote

    model = LocalMedicalModel()

    # Simulate a transcript that STT would produce
    transcript = (
        "My skin has been very itchy for the past week. "
        "There are red bumps on my arms and neck. "
        "It gets worse at night."
    )

    soap = await model.generate_soap(
        transcript=transcript,
        image_context="Papular rash visible on upper arms and neck region.",
        rag_context="Similar presentations in SCIN database: L20.0 Atopic dermatitis.",
    )

    assert isinstance(soap, SOAPNote)
    assert len(soap.subjective) > 0
    assert soap.disclaimer != ""
