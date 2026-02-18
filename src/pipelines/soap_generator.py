"""SOAP note generator.

Generates SOAP-formatted case histories from patient interview data,
image analysis, and RAG context. Includes ICD code suggestions.

Covers: Phase 5 tasks
"""

from __future__ import annotations

import structlog

from src.models.medical_model import get_medical_model
from src.models.protocols.medical import SOAPNote
from src.models.rag_retrieval import RetrievalResponse
from src.utils.session import PatientSession

logger = structlog.get_logger(__name__)

DISCLAIMER = (
    "This is an AI-assisted triage assessment, not a medical diagnosis. "
    "Please seek professional medical help for proper evaluation and treatment."
)


async def generate_soap_note(
    session: PatientSession,
    rag_results: RetrievalResponse | None = None,
    image_analysis: str = "",
) -> SOAPNote:
    """Generate a SOAP note from patient session data.

    Args:
        session: Patient session with transcript and metadata.
        rag_results: Optional RAG retrieval results for context.
        image_analysis: Optional image analysis text.

    Returns:
        SOAPNote with all four sections, ICD codes, and disclaimer.
    """
    model = get_medical_model()

    # Build context from RAG results
    rag_context = ""
    if rag_results and rag_results.results:
        rag_context = "Similar cases from the dermatology database:\n"
        for r in rag_results.results[:5]:
            rag_context += f"- {r.diagnosis} (ICD: {r.icd_code}, similarity: {r.score:.2f})\n"

    # Build transcript
    transcript = "\n".join(session.transcript) if session.transcript else "No transcript available."

    soap = await model.generate_soap(
        transcript=transcript,
        image_context=image_analysis,
        rag_context=rag_context,
    )

    # Always include the disclaimer
    soap.disclaimer = DISCLAIMER

    logger.info(
        "soap_generated",
        session_id=session.session_id,
        icd_codes=soap.icd_codes,
        confidence=f"{soap.confidence:.2f}",
        has_rag_context=bool(rag_context),
        has_image=bool(image_analysis),
    )

    return soap
