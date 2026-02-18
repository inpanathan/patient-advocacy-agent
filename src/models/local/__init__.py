"""Local model implementations using on-device GPU inference.

Provides MedGemma 4B, SigLIP-2, Faster-Whisper, and Piper TTS
for fully offline operation.
"""

from src.models.local.local_embedding import LocalEmbeddingModel
from src.models.local.local_language_detection import LocalLanguageDetector
from src.models.local.local_medical import LocalMedicalModel
from src.models.local.local_stt import LocalSTT
from src.models.local.local_tts import LocalTTS

__all__ = [
    "LocalEmbeddingModel",
    "LocalLanguageDetector",
    "LocalMedicalModel",
    "LocalSTT",
    "LocalTTS",
]
