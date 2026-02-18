"""Cloud model implementations using Google Cloud APIs.

Provides Gemini API for LLM, Google Cloud STT/TTS for voice,
and shares SigLIP-2 for embeddings (no cloud equivalent).
"""

from src.models.cloud.cloud_language_detection import CloudLanguageDetector
from src.models.cloud.cloud_medical import CloudMedicalModel
from src.models.cloud.cloud_stt import CloudSTT
from src.models.cloud.cloud_tts import CloudTTS

__all__ = [
    "CloudLanguageDetector",
    "CloudMedicalModel",
    "CloudSTT",
    "CloudTTS",
]
