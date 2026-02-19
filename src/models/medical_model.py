"""Medical AI model integration (MedGemma).

Provides the medical LLM for SOAP note generation, ICD coding,
patient interview, and clinical reasoning.

Covers: REQ-CST-009
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_medical import MockMedicalModel
from src.models.protocols.medical import MedicalModelProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)

_instance: MedicalModelProtocol | None = None


def get_medical_model() -> MedicalModelProtocol:
    """Factory to get the medical AI model based on model_backend setting.

    Returns a singleton instance to avoid loading the model multiple times
    (each LocalMedicalModel copy consumes ~8 GB VRAM).
    """
    global _instance  # noqa: PLW0603
    if _instance is not None:
        return _instance

    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_medical_model")
        _instance = MockMedicalModel()
        return _instance

    if backend == "local":
        try:
            from src.models.local.local_medical import LocalMedicalModel

            logger.info("using_local_medical_model")
            _instance = LocalMedicalModel()
            return _instance
        except ImportError as exc:
            logger.warning("local_medical_model_unavailable_falling_back_to_mock", error=str(exc))
            _instance = MockMedicalModel()
            return _instance

    if backend == "cloud":
        from src.models.cloud.cloud_medical import CloudMedicalModel

        logger.info("using_cloud_medical_model")
        _instance = CloudMedicalModel()
        return _instance

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
