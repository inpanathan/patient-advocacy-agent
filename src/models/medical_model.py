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


def get_medical_model() -> MedicalModelProtocol:
    """Factory to get the medical AI model based on model_backend setting."""
    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_medical_model")
        return MockMedicalModel()

    if backend == "local":
        from src.models.local.local_medical import LocalMedicalModel

        logger.info("using_local_medical_model")
        return LocalMedicalModel()

    if backend == "cloud":
        from src.models.cloud.cloud_medical import CloudMedicalModel

        logger.info("using_cloud_medical_model")
        return CloudMedicalModel()

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)
