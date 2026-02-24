"""Patient explanation generator.

Produces simple, plain-language explanations of the assessment
for patients in their own language, suitable for text-to-speech delivery.

Covers: Phase 5 tasks
"""

from __future__ import annotations

import structlog

from src.models.medical_model import get_medical_model
from src.models.protocols.medical import SOAPNote

logger = structlog.get_logger(__name__)

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "sw": "Swahili",
    "es": "Spanish",
}


async def generate_patient_explanation(
    soap: SOAPNote,
    language: str = "en",
) -> str:
    """Generate a simple patient-facing explanation in the patient's language.

    Args:
        soap: The SOAP note for this case.
        language: Patient's detected language code.

    Returns:
        Plain-language explanation suitable for TTS.
    """
    model = get_medical_model()
    lang_name = LANGUAGE_NAMES.get(language, "English")

    response = await model.generate(
        prompt=(
            f"Based on this medical assessment:\n{soap.assessment}\n\n"
            f"Plan:\n{soap.plan}\n\n"
            f"Write a simple, reassuring explanation for the patient in {lang_name}.\n"
            "Rules:\n"
            "- Use very short, simple sentences (the patient may be illiterate).\n"
            "- Do NOT prescribe medication or make a definitive diagnosis.\n"
            "- Do NOT use medical jargon or ICD codes.\n"
            "- Always recommend seeing a doctor in person.\n"
            "- Include a disclaimer that this is NOT a medical diagnosis.\n"
            f"- Write ONLY in {lang_name}. Do not mix languages.\n"
            "- Keep it under 6 sentences.\n"
        ),
        max_tokens=200,
    )

    logger.info(
        "patient_explanation_generated",
        language=language,
        icd_codes=soap.icd_codes,
    )

    return response.text.strip()
