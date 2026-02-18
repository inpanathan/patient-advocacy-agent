"""Case history formatter for physicians.

Formats the SOAP note and supporting data into a formal case history
report for remote healthcare facility physicians.

Covers: Phase 5 tasks
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, Field

from src.models.protocols.medical import SOAPNote
from src.utils.session import PatientSession

logger = structlog.get_logger(__name__)


class CaseHistory(BaseModel):
    """Formal case history report for physicians."""

    case_id: str = ""
    session_id: str = ""
    generated_at: str = Field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )
    patient_language: str = ""
    soap_note: dict = Field(default_factory=dict)
    icd_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    rag_similar_cases: list[str] = Field(default_factory=list)
    images_captured: int = 0
    escalated: bool = False
    escalation_reason: str = ""
    disclaimer: str = (
        "This is an AI-assisted triage assessment, not a medical diagnosis. "
        "Please seek professional medical help for proper evaluation and treatment."
    )


def format_case_history(
    session: PatientSession,
    soap: SOAPNote,
    similar_diagnoses: list[str] | None = None,
) -> CaseHistory:
    """Format a case history from session and SOAP data.

    Args:
        session: Patient session with all interaction data.
        soap: Generated SOAP note.
        similar_diagnoses: List of similar diagnoses from RAG.

    Returns:
        Formatted CaseHistory ready for delivery to physician.
    """
    case = CaseHistory(
        case_id=f"CASE-{session.session_id[:8].upper()}",
        session_id=session.session_id,
        patient_language=session.detected_language,
        soap_note={
            "subjective": soap.subjective,
            "objective": soap.objective,
            "assessment": soap.assessment,
            "plan": soap.plan,
        },
        icd_codes=soap.icd_codes,
        confidence=soap.confidence,
        rag_similar_cases=similar_diagnoses or [],
        images_captured=len(session.captured_images),
        escalated=session.escalated,
        escalation_reason=session.escalation_reason,
    )

    logger.info(
        "case_history_formatted",
        case_id=case.case_id,
        session_id=session.session_id,
        icd_codes=case.icd_codes,
        escalated=case.escalated,
    )

    return case
