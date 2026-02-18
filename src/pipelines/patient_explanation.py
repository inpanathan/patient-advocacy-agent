"""Patient explanation generator.

Produces simple, plain-language explanations of the assessment
for patients, suitable for text-to-speech delivery.

Covers: Phase 5 tasks
"""

from __future__ import annotations

import structlog

from src.models.medical_model import get_medical_model
from src.models.protocols.medical import SOAPNote

logger = structlog.get_logger(__name__)

DISCLAIMER = (
    "Remember, I am not a doctor. Please visit a healthcare center "
    "for proper medical care."
)


async def generate_patient_explanation(
    soap: SOAPNote,
    language: str = "en",
) -> str:
    """Generate a simple patient-facing explanation.

    Args:
        soap: The SOAP note for this case.
        language: Patient's detected language.

    Returns:
        Plain-language explanation suitable for TTS.
    """
    model = get_medical_model()

    response = await model.generate(
        prompt=(
            f"Based on this assessment:\n{soap.assessment}\n\n"
            "Generate a simple, reassuring explanation for a patient "
            "who may not be literate. Use short sentences. "
            "Do NOT prescribe medication or make a definitive diagnosis. "
            "Always recommend seeing a doctor."
        ),
    )

    explanation = response.text + f"\n\n{DISCLAIMER}"

    logger.info(
        "patient_explanation_generated",
        language=language,
        icd_codes=soap.icd_codes,
    )

    return explanation
