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


def _deduplicate_lines(text: str) -> str:
    """Remove consecutive duplicate lines and strip prompt leakage."""
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip prompt instruction leakage
        if line.startswith("- ") and any(
            line.lower().startswith(prefix)
            for prefix in [
                "- use ",
                "- do ",
                "- write ",
                "- keep ",
                "- include ",
                "- always ",
            ]
        ):
            continue
        # Skip exact duplicate sentences
        normalized = line.rstrip(".")
        if normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line)
    return "\n".join(lines)


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
            f"You are explaining a skin check result to a patient in {lang_name}.\n\n"
            f"Assessment: {soap.assessment}\n"
            f"Plan: {soap.plan}\n\n"
            f"Write 4-5 short sentences in {lang_name} for the patient. "
            "Do not repeat any sentence. "
            "Do not prescribe medication or diagnose. "
            "Tell them to see a doctor in person. "
            "Remind them this is not a medical diagnosis."
        ),
        max_tokens=250,
    )

    result = _deduplicate_lines(response.text.strip())

    logger.info(
        "patient_explanation_generated",
        language=language,
        icd_codes=soap.icd_codes,
    )

    return result
