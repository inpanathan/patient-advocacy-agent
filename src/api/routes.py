"""API routes for the Patient Advocacy Agent.

Defines all HTTP endpoints for the application:
- Health check
- Session management
- Voice interaction
- SOAP generation
- Case history retrieval

Covers: Phase 6 tasks, REQ-DOC-005, REQ-SEC-007
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.protocols.voice import STTResult
from src.pipelines.case_history import format_case_history
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.logger import get_logger
from src.utils.session import SessionStore

logger = get_logger(__name__)

router = APIRouter()

# Singletons (initialized at app startup)
_session_store = SessionStore()
_interview_agent = PatientInterviewAgent()


# ---- Request/Response Models ----


class CreateSessionResponse(BaseModel):
    session_id: str
    stage: str


class InteractRequest(BaseModel):
    text: str
    language: str = "en"
    confidence: float = 0.9


class InteractResponse(BaseModel):
    response: str
    stage: str
    session_id: str


class ConsentRequest(BaseModel):
    consent: bool


class SOAPResponse(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    icd_codes: list[str]
    confidence: float
    disclaimer: str


class CaseHistoryResponse(BaseModel):
    case_id: str
    session_id: str
    soap_note: dict
    icd_codes: list[str]
    escalated: bool
    disclaimer: str


class ErrorResponse(BaseModel):
    error: dict


# ---- Endpoints ----


@router.post("/sessions", response_model=CreateSessionResponse, tags=["sessions"])
async def create_session():
    """Create a new patient interaction session."""
    session = _session_store.create()
    logger.info("api_session_created", session_id=session.session_id)
    return CreateSessionResponse(
        session_id=session.session_id,
        stage=session.stage,
    )


@router.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(session_id: str):
    """Get session status."""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "stage": session.stage,
        "language": session.detected_language,
        "transcript_length": len(session.transcript),
        "image_consent": session.image_consent_given,
        "escalated": session.escalated,
    }


@router.post(
    "/sessions/{session_id}/interact",
    response_model=InteractResponse,
    tags=["interaction"],
)
async def interact(session_id: str, request: InteractRequest):
    """Process a patient utterance and get agent response.

    This is the main interaction endpoint. Send the transcribed text
    and get back the agent's response (to be spoken via TTS).
    """
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    stt_result = STTResult(
        text=request.text,
        language=request.language,
        confidence=request.confidence,
        duration_ms=0,
    )

    response_text = await _interview_agent.process_utterance(session, stt_result)

    logger.info(
        "api_interaction",
        session_id=session_id,
        stage=session.stage,
        input_length=len(request.text),
    )

    return InteractResponse(
        response=response_text,
        stage=session.stage,
        session_id=session_id,
    )


@router.post("/sessions/{session_id}/consent", tags=["interaction"])
async def update_consent(session_id: str, request: ConsentRequest):
    """Record patient consent for image capture."""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.consent:
        session.grant_image_consent()
    return {"consent": session.image_consent_given}


@router.post(
    "/sessions/{session_id}/soap",
    response_model=SOAPResponse,
    tags=["medical"],
)
async def generate_soap(session_id: str):
    """Generate a SOAP note for the session.

    Requires at least some transcript data from the interview.
    """
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.transcript:
        raise HTTPException(status_code=400, detail="No transcript data available")

    soap = await generate_soap_note(session)

    # Check for escalation
    escalation = _interview_agent.check_escalation(
        f"{soap.assessment} {soap.plan}"
    )
    if escalation:
        session.mark_escalated(escalation)

    return SOAPResponse(
        subjective=soap.subjective,
        objective=soap.objective,
        assessment=soap.assessment,
        plan=soap.plan,
        icd_codes=soap.icd_codes,
        confidence=soap.confidence,
        disclaimer=soap.disclaimer,
    )


@router.get(
    "/sessions/{session_id}/case-history",
    response_model=CaseHistoryResponse,
    tags=["medical"],
)
async def get_case_history(session_id: str):
    """Get the formatted case history for physician review."""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    soap = await generate_soap_note(session)
    case = format_case_history(session, soap)

    return CaseHistoryResponse(
        case_id=case.case_id,
        session_id=case.session_id,
        soap_note=case.soap_note,
        icd_codes=case.icd_codes,
        escalated=case.escalated,
        disclaimer=case.disclaimer,
    )


@router.delete("/sessions/{session_id}", tags=["sessions"])
async def delete_session(session_id: str):
    """Delete a session and all associated data."""
    deleted = _session_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}
