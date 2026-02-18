"""API routes for the Patient Advocacy Agent.

Defines all HTTP endpoints for the application:
- Health check
- Session management
- Voice interaction (text + audio)
- Image upload with RAG
- SOAP generation
- Case history retrieval

Covers: Phase 6 tasks, REQ-DOC-005, REQ-SEC-007
"""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from src.models.protocols.voice import STTResult
from src.models.rag_retrieval import RAGRetriever
from src.models.stt import get_stt_service
from src.models.tts import get_tts_service
from src.pipelines.case_history import format_case_history
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.logger import get_logger
from src.utils.session import SessionStage, SessionStore

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


class AudioInteractResponse(BaseModel):
    response: str
    audio_base64: str
    audio_format: str
    stage: str
    session_id: str
    detected_language: str
    stt_confidence: float


class ImageUploadResponse(BaseModel):
    image_id: str
    session_id: str
    similar_cases: list[dict]
    image_analysis: str


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


# ---- Helpers ----


def _ensure_upload_dir(session_id: str) -> Path:
    """Create and return the upload directory for a session."""
    upload_dir = Path("data/uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _get_retriever(request: Request) -> RAGRetriever | None:
    """Get RAG retriever from app state, or None if unavailable."""
    return getattr(request.app.state, "rag_retriever", None)


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


@router.post(
    "/sessions/{session_id}/audio",
    response_model=AudioInteractResponse,
    tags=["interaction"],
)
async def audio_interact(session_id: str, audio: Annotated[UploadFile, File()]):
    """Process raw audio from the UI microphone.

    Runs STT on the uploaded audio, processes the utterance through the
    interview agent, then synthesizes the response via TTS.
    Returns both the text response and base64-encoded audio.
    """
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_bytes = await audio.read()

    # STT: audio -> text
    stt_service = get_stt_service()
    stt_result = await stt_service.transcribe(audio_bytes, language_hint=session.detected_language)

    # Process through interview agent
    response_text = await _interview_agent.process_utterance(session, stt_result)

    # TTS: text -> audio
    tts_service = get_tts_service()
    tts_result = await tts_service.synthesize(
        response_text, language=session.detected_language or "en"
    )

    logger.info(
        "api_audio_interaction",
        session_id=session_id,
        stage=session.stage,
        stt_language=stt_result.language,
        stt_confidence=stt_result.confidence,
    )

    return AudioInteractResponse(
        response=response_text,
        audio_base64=base64.b64encode(tts_result.audio_bytes).decode("ascii"),
        audio_format=tts_result.format,
        stage=session.stage,
        session_id=session_id,
        detected_language=stt_result.language,
        stt_confidence=stt_result.confidence,
    )


@router.post(
    "/sessions/{session_id}/image",
    response_model=ImageUploadResponse,
    tags=["interaction"],
)
async def upload_image(
    session_id: str,
    request: Request,
    image: Annotated[UploadFile, File()],
):
    """Upload an image for dermatological analysis.

    Requires image consent to have been granted. Saves the image,
    runs RAG retrieval for similar cases, and stores the analysis
    on the session for later SOAP generation.
    """
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.image_consent_given:
        raise HTTPException(
            status_code=403,
            detail="Image consent not granted. Call /consent first.",
        )

    # Save uploaded image
    upload_dir = _ensure_upload_dir(session_id)
    image_id = str(uuid.uuid4())
    image_ext = Path(image.filename or "photo.jpg").suffix or ".jpg"
    image_path = upload_dir / f"{image_id}{image_ext}"
    image_bytes = await image.read()
    image_path.write_bytes(image_bytes)
    session.captured_images.append(str(image_path))

    # RAG: query by image for similar cases
    similar_cases: list[dict] = []
    image_analysis = ""
    retriever = _get_retriever(request)
    if retriever:
        try:
            rag_response = retriever.query_by_image(str(image_path))
            for r in rag_response.results[:5]:
                similar_cases.append(
                    {
                        "diagnosis": r.diagnosis,
                        "icd_code": r.icd_code,
                        "score": round(r.score, 4),
                    }
                )
            if similar_cases:
                lines = [
                    f"- {c['diagnosis']} (ICD: {c['icd_code']}, score: {c['score']})"
                    for c in similar_cases
                ]
                image_analysis = "Similar dermatological cases:\n" + "\n".join(lines)
        except Exception as exc:
            logger.warning(
                "image_rag_failed",
                session_id=session_id,
                error=str(exc),
            )

    session.image_analysis = image_analysis
    session.advance_to(SessionStage.ANALYSIS)

    logger.info(
        "api_image_uploaded",
        session_id=session_id,
        image_id=image_id,
        similar_cases_count=len(similar_cases),
    )

    return ImageUploadResponse(
        image_id=image_id,
        session_id=session_id,
        similar_cases=similar_cases,
        image_analysis=image_analysis,
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
async def generate_soap(session_id: str, request: Request):
    """Generate a SOAP note for the session.

    Queries RAG for relevant context and includes any image analysis
    from prior uploads. Requires at least some transcript data.
    """
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.transcript:
        raise HTTPException(status_code=400, detail="No transcript data available")

    # RAG: query by transcript text
    rag_results = None
    retriever = _get_retriever(request)
    if retriever:
        try:
            text_query = " ".join(session.transcript)
            rag_results = retriever.query_by_text(text_query)
        except Exception as exc:
            logger.warning(
                "soap_rag_failed",
                session_id=session_id,
                error=str(exc),
            )

    soap = await generate_soap_note(
        session,
        rag_results=rag_results,
        image_analysis=session.image_analysis,
    )

    # Check for escalation
    escalation = _interview_agent.check_escalation(f"{soap.assessment} {soap.plan}")
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
