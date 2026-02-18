"""Medical AI model integration (MedGemma).

Provides the medical LLM for SOAP note generation, ICD coding,
patient interview, and clinical reasoning.

TODO: Requires MEDGEMMA_API_KEY for real implementation.

Covers: REQ-CST-009
"""

from __future__ import annotations

import structlog

from src.models.mocks.mock_medical import MockMedicalModel
from src.models.protocols.medical import MedicalModelProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_medical_model() -> MedicalModelProtocol:
    """Factory to get the medical AI model."""
    if settings.use_mocks:
        logger.info("using_mock_medical_model")
        return MockMedicalModel()

    # TODO: Real MedGemma integration
    logger.warning("real_medical_model_not_available", fallback="mock")
    return MockMedicalModel()
