"""Patient explanation generator.

Produces simple, plain-language explanations of the assessment
for patients in their own language, suitable for text-to-speech delivery.

Covers: Phase 5 tasks
"""

from __future__ import annotations

import re

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

# Regex patterns for meta-commentary the model adds around translations
_META_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^here'?s?\s+(a\s+)?(the\s+)?", re.IGNORECASE),
    re.compile(r"^breakdown\s+of\s+", re.IGNORECASE),
    re.compile(r"^translation:?\s*$", re.IGNORECASE),
    re.compile(r"^(note|explanation|summary)\s*:", re.IGNORECASE),
    re.compile(r"^\*\*", re.IGNORECASE),
]


def _is_meta_line(line: str) -> bool:
    """Return True if the line is model meta-commentary, not patient text."""
    lower = line.lower().strip().rstrip(":")
    # Prompt instruction leakage ("- Use ...", "- Do ...", etc.)
    if line.startswith("- ") and any(
        lower.startswith(p)
        for p in [
            "- use ",
            "- do ",
            "- write ",
            "- keep ",
            "- include ",
            "- always ",
            "- note",
        ]
    ):
        return True
    # English meta-commentary around translations
    return any(pattern.search(lower) for pattern in _META_PATTERNS)


def _deduplicate_lines(text: str) -> str:
    """Remove duplicate lines and strip prompt leakage / meta-commentary."""
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_meta_line(line):
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
            f"Write exactly 4 short sentences in {lang_name} only. "
            "Do not repeat any sentence. "
            "Do not add any English text or commentary. "
            "Do not prescribe medication or diagnose. "
            "Tell them to see a doctor in person. "
            "Remind them this is not a medical diagnosis.\n\n"
            f"{lang_name}:"
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
