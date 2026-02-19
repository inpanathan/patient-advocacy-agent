"""Mock medical AI model for development and testing.

Provides mock MedGemma responses including SOAP note generation
and ICD coding without requiring API access.
"""

from __future__ import annotations

import structlog

from src.models.protocols.medical import MedicalModelResponse, SOAPNote

logger = structlog.get_logger(__name__)


class MockMedicalModel:
    """Mock MedGemma medical AI model."""

    def __init__(self, model_id: str = "mock-medgemma-v1") -> None:
        self.model_id = model_id
        logger.info("mock_medical_model_loaded", model_id=model_id)

    async def generate(
        self, prompt: str, *, temperature: float = 0.3, max_tokens: int = 0
    ) -> MedicalModelResponse:
        """Generate a mock response."""
        return MedicalModelResponse(
            text=(
                "Based on the described symptoms, this appears consistent with "
                "a common dermatological condition. Please seek professional medical "
                "evaluation for proper diagnosis and treatment."
            ),
            model_id=self.model_id,
            prompt_tokens=len(prompt.split()),
            completion_tokens=30,
            latency_ms=150,
        )

    async def generate_soap(
        self,
        transcript: str,
        image_context: str = "",
        rag_context: str = "",
    ) -> SOAPNote:
        """Generate a mock SOAP note."""
        return SOAPNote(
            subjective=(
                "Patient reports a skin condition on the affected area. "
                "Symptoms include itching, redness, and mild discomfort. "
                "Duration: approximately 3 days."
            ),
            objective=(
                "Visual assessment via captured image shows erythematous "
                "patches with mild scaling. No signs of secondary infection. "
                "RAG retrieval suggests similarity to eczematous conditions."
            ),
            assessment=(
                "Presentation is consistent with atopic dermatitis (ICD L20.0). "
                "Differential includes contact dermatitis (L25.0). "
                "No signs of malignancy. Low urgency."
            ),
            plan=(
                "1. Recommend patient seek evaluation at nearest healthcare facility. "
                "2. Suggest moisturizer application for symptomatic relief. "
                "3. Return if symptoms worsen or new symptoms develop. "
                "4. Case history forwarded to remote physician for review."
            ),
            icd_codes=["L20.0", "L25.0"],
            confidence=0.78,
        )
