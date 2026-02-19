"""Case lifecycle endpoints for admins (patient mode)."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.case_session_bridge import CaseSessionBridge
from src.api.schemas import (
    CaseImageResponse,
    CaseResponse,
    CaseSummaryResponse,
    StartCaseRequest,
)
from src.auth.dependencies import require_role
from src.db.engine import get_session
from src.db.models import AudioRole, CaseStatus, User
from src.db.repositories.assignment import AssignmentRepository
from src.db.repositories.case_repo import CaseRepository
from src.models.rag_retrieval import RAGRetriever
from src.models.stt import get_stt_service
from src.models.tts import get_tts_service
from src.observability.metrics import record_prediction, record_retrieval
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cases", tags=["cases"])

_interview_agent = PatientInterviewAgent()


def _get_bridge(request: Request) -> CaseSessionBridge:
    """Get the CaseSessionBridge from app state."""
    return request.app.state.case_session_bridge  # type: ignore[no-any-return]


def _get_retriever(request: Request) -> RAGRetriever | None:
    return getattr(request.app.state, "rag_retriever", None)


def _get_audit_trail(request: Request):  # type: ignore[no-untyped-def]
    """Get the AuditTrail from dashboard aggregator state."""
    agg = getattr(request.app.state, "dashboard_aggregator", None)
    if agg is not None:
        return getattr(agg._state, "audit_trail", None)
    return None


@router.post("/", response_model=CaseResponse)
async def start_case(
    body: StartCaseRequest,
    request: Request,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    """Start a new case: auto-assigns a doctor via least-loaded algorithm."""
    facility_id = uuid.UUID(body.facility_id)
    patient_id = uuid.UUID(body.patient_id)

    # Assign doctor
    assign_repo = AssignmentRepository(session)
    doctor_id = await assign_repo.assign_least_loaded_doctor(facility_id)

    # Generate case number and create
    case_repo = CaseRepository(session)
    case_number = await case_repo.generate_case_number(facility_id)
    case = await case_repo.create_case(
        case_number=case_number,
        facility_id=facility_id,
        patient_id=patient_id,
        admin_id=user.id,
        doctor_id=doctor_id,
    )

    logger.info(
        "case_started",
        case_id=str(case.id),
        case_number=case.case_number,
        doctor_id=str(doctor_id) if doctor_id else None,
    )

    return CaseResponse(
        id=str(case.id),
        case_number=case.case_number,
        facility_id=str(case.facility_id),
        patient_id=str(case.patient_id),
        admin_id=str(case.admin_id),
        doctor_id=str(case.doctor_id) if case.doctor_id else None,
        status=case.status.value,
        escalated=case.escalated,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("/", response_model=list[CaseResponse])
async def list_cases(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[CaseResponse]:
    """List cases for the admin's facility, optionally filtered by status."""
    case_repo = CaseRepository(session)

    filter_status = None
    if status:
        try:
            filter_status = CaseStatus(status)
        except ValueError:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid status: {status}",
            ) from None

    cases = await case_repo.list_facility_cases(
        facility_id=user.facility_id,
        status=filter_status,
        limit=limit,
        offset=offset,
    )

    logger.info(
        "admin_cases_listed",
        facility_id=str(user.facility_id),
        count=len(cases),
        status_filter=status,
    )

    return [
        CaseResponse(
            id=str(c.id),
            case_number=c.case_number,
            facility_id=str(c.facility_id),
            patient_id=str(c.patient_id),
            admin_id=str(c.admin_id),
            doctor_id=str(c.doctor_id) if c.doctor_id else None,
            status=c.status.value,
            escalated=c.escalated,
            image_count=len(c.images) if c.images else 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    """Get case details."""
    repo = CaseRepository(session)
    case = await repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")
    return CaseResponse(
        id=str(case.id),
        case_number=case.case_number,
        facility_id=str(case.facility_id),
        patient_id=str(case.patient_id),
        admin_id=str(case.admin_id),
        doctor_id=str(case.doctor_id) if case.doctor_id else None,
        status=case.status.value,
        escalated=case.escalated,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("/{case_id}/greet")
async def greet(
    case_id: str,
    request: Request,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the assistant greeting with TTS for a case (no audio input needed)."""
    bridge = _get_bridge(request)
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    patient_session = bridge.get_or_create(case.id)

    greeting_text = (
        "Hello, I am a health assistant. I am not a doctor. "
        "I will ask you some questions to help a doctor understand your condition. "
        "Please press and hold the microphone button to speak."
    )

    # Advance past greeting so the first audio goes straight to interview
    from src.utils.session import SessionStage

    if patient_session.stage == SessionStage.GREETING:
        patient_session.advance_to(SessionStage.INTERVIEW)

    tts_service = get_tts_service()
    tts_result = await tts_service.synthesize(
        greeting_text, language=patient_session.detected_language or "en"
    )

    return {
        "response": greeting_text,
        "audio_base64": base64.b64encode(tts_result.audio_bytes).decode("ascii"),
        "audio_format": tts_result.format,
        "stage": patient_session.stage,
    }


@router.post("/{case_id}/audio")
async def process_audio(
    case_id: str,
    request: Request,
    audio: Annotated[UploadFile, File()],
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Process audio for a case: STT → interview agent → TTS."""
    bridge = _get_bridge(request)
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    patient_session = bridge.get_or_create(case.id)
    audio_bytes = await audio.read()

    # STT
    stt_service = get_stt_service()
    stt_result = await stt_service.transcribe(
        audio_bytes, language_hint=patient_session.detected_language
    )

    # If STT returned empty text (corrupted/too-short audio), ask to try again
    if not stt_result.text.strip():
        return {
            "response": "I could not hear you clearly. Please hold the button and speak again.",
            "stt_text": "",
            "audio_base64": "",
            "audio_format": "wav",
            "stage": patient_session.stage,
            "detected_language": patient_session.detected_language or "en",
        }

    # Save patient audio to DB
    await case_repo.add_audio(
        case_id=case.id,
        role=AudioRole.patient,
        transcript=stt_result.text,
        duration_ms=stt_result.duration_ms,
    )

    # Interview agent
    response_text = await _interview_agent.process_utterance(patient_session, stt_result)

    # Save system response audio to DB
    await case_repo.add_audio(
        case_id=case.id,
        role=AudioRole.system,
        transcript=response_text,
    )

    # TTS
    tts_service = get_tts_service()
    tts_result = await tts_service.synthesize(
        response_text, language=patient_session.detected_language or "en"
    )

    return {
        "response": response_text,
        "stt_text": stt_result.text,
        "audio_base64": base64.b64encode(tts_result.audio_bytes).decode("ascii"),
        "audio_format": tts_result.format,
        "stage": patient_session.stage,
        "detected_language": stt_result.language,
    }


@router.post("/{case_id}/consent")
async def record_consent(
    case_id: str,
    request: Request,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Record image consent for a case."""
    bridge = _get_bridge(request)
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    patient_session = bridge.get_or_create(case.id)
    patient_session.grant_image_consent()
    return {"consent": True}


@router.post("/{case_id}/image")
async def upload_image(
    case_id: str,
    request: Request,
    image: Annotated[UploadFile, File()],
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Upload an image for a case with RAG analysis."""
    bridge = _get_bridge(request)
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    patient_session = bridge.get_or_create(case.id)
    if not patient_session.image_consent_given:
        raise AppError(
            code=ErrorCode.FORBIDDEN,
            message="Image consent not granted. Call /consent first.",
        )

    # Save image file
    upload_dir = Path("data/uploads") / case_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_id = str(uuid.uuid4())
    ext = Path(image.filename or "photo.jpg").suffix or ".jpg"
    image_path = upload_dir / f"{image_id}{ext}"
    image_bytes = await image.read()
    image_path.write_bytes(image_bytes)

    # RAG retrieval (image)
    import time as _time

    rag_results_data: dict | None = None
    retriever = _get_retriever(request)
    if retriever:
        try:
            _rag_t0 = _time.monotonic()
            rag_response = retriever.query_by_image(str(image_path))
            _rag_ms = (_time.monotonic() - _rag_t0) * 1000
            rag_results_data = {
                "results": [
                    {"diagnosis": r.diagnosis, "icd_code": r.icd_code, "score": round(r.score, 4)}
                    for r in rag_response.results[:5]
                ]
            }
            record_retrieval(
                query_type="image",
                num_results=len(rag_response.results),
                top_score=rag_response.results[0].score if rag_response.results else 0.0,
                latency_ms=_rag_ms,
            )
        except Exception as exc:
            logger.warning("case_image_rag_failed", case_id=case_id, error=str(exc))

    # Save image to DB
    db_image = await case_repo.add_image(
        case_id=case.id,
        file_path=str(image_path),
        consent_given=True,
        rag_results=rag_results_data,
    )

    # Store image analysis context on the session for SOAP generation
    if rag_results_data and rag_results_data.get("results"):
        analysis_lines = ["Image RAG analysis (similar dermatological cases):"]
        for r in rag_results_data["results"]:
            analysis_lines.append(
                f"- {r['diagnosis']} (ICD: {r['icd_code']}, similarity: {r['score']})"
            )
        patient_session.image_analysis = "\n".join(analysis_lines)

    # Auto-generate SOAP assessment using transcript + image
    retriever = _get_retriever(request)
    text_rag_results = None
    if retriever and patient_session.transcript:
        try:
            _text_rag_t0 = _time.monotonic()
            text_query = " ".join(patient_session.transcript)
            text_rag_results = retriever.query_by_text(text_query)
            _text_rag_ms = (_time.monotonic() - _text_rag_t0) * 1000
            record_retrieval(
                query_type="text",
                num_results=len(text_rag_results.results) if text_rag_results else 0,
                top_score=text_rag_results.results[0].score
                if text_rag_results and text_rag_results.results
                else 0.0,
                latency_ms=_text_rag_ms,
            )
        except Exception as exc:
            logger.warning("image_rag_text_failed", case_id=case_id, error=str(exc))

    _soap_t0 = _time.monotonic()
    soap = await generate_soap_note(
        patient_session,
        rag_results=text_rag_results,
        image_analysis=patient_session.image_analysis,
    )
    _soap_ms = (_time.monotonic() - _soap_t0) * 1000

    # Check escalation
    escalation = _interview_agent.check_escalation(f"{soap.assessment} {soap.plan}")
    escalated = bool(escalation)

    # Record prediction metrics for dashboard
    record_prediction(
        session_id=patient_session.session_id,
        icd_codes=soap.icd_codes,
        confidence=soap.confidence,
        escalated=escalated,
        latency_ms=_soap_ms,
        language=patient_session.detected_language or "en",
    )

    # Record audit trail
    audit_trail = _get_audit_trail(request)
    if audit_trail:
        from src.observability.audit import AuditRecord

        audit_trail.record(
            AuditRecord(
                trace_id=patient_session.trace_id,
                session_id=patient_session.session_id,
                icd_codes=soap.icd_codes,
                confidence=soap.confidence,
                escalated=escalated,
                escalation_reason=escalation or "",
                image_captured=True,
                patient_language=patient_session.detected_language or "en",
            )
        )

    # Build transcript and complete case in DB
    transcript = (
        patient_session.conversation
        if patient_session.conversation
        else [{"role": "patient", "text": t} for t in patient_session.transcript]
    )
    soap_dict = {
        "subjective": soap.subjective,
        "objective": soap.objective,
        "assessment": soap.assessment,
        "plan": soap.plan,
        "disclaimer": soap.disclaimer,
    }
    case = await case_repo.complete_case(
        case_id=case.id,
        soap_note=soap_dict,
        icd_codes=soap.icd_codes,
        interview_transcript=transcript,
        escalated=escalated,
    )

    # Discard in-memory session
    bridge.discard(case.id)  # type: ignore[union-attr]

    logger.info(
        "case_auto_completed_after_image",
        case_id=case_id,
        escalated=escalated,
        icd_codes=soap.icd_codes,
    )

    return {
        "image_id": str(db_image.id),
        "rag_results": rag_results_data,
        "completed": True,
    }


@router.post("/{case_id}/complete", response_model=CaseSummaryResponse)
async def complete_case(
    case_id: str,
    request: Request,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> CaseSummaryResponse:
    """Complete a case: generate SOAP, write to DB, discard session."""
    bridge = _get_bridge(request)
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    patient_session = bridge.get_or_create(case.id)

    # Generate SOAP note
    import time as _time

    retriever = _get_retriever(request)
    rag_results = None
    if retriever and patient_session.transcript:
        try:
            _rag_t0 = _time.monotonic()
            text_query = " ".join(patient_session.transcript)
            rag_results = retriever.query_by_text(text_query)
            _rag_ms = (_time.monotonic() - _rag_t0) * 1000
            record_retrieval(
                query_type="text",
                num_results=len(rag_results.results) if rag_results else 0,
                top_score=rag_results.results[0].score
                if rag_results and rag_results.results
                else 0.0,
                latency_ms=_rag_ms,
            )
        except Exception as exc:
            logger.warning("complete_rag_failed", case_id=case_id, error=str(exc))

    _soap_t0 = _time.monotonic()
    soap = await generate_soap_note(
        patient_session,
        rag_results=rag_results,
        image_analysis=patient_session.image_analysis,
    )
    _soap_ms = (_time.monotonic() - _soap_t0) * 1000

    # Check escalation
    escalation = _interview_agent.check_escalation(f"{soap.assessment} {soap.plan}")
    escalated = bool(escalation)

    # Record prediction metrics for dashboard
    record_prediction(
        session_id=patient_session.session_id,
        icd_codes=soap.icd_codes,
        confidence=soap.confidence,
        escalated=escalated,
        latency_ms=_soap_ms,
        language=patient_session.detected_language or "en",
    )

    # Record audit trail
    audit_trail = _get_audit_trail(request)
    if audit_trail:
        from src.observability.audit import AuditRecord

        audit_trail.record(
            AuditRecord(
                trace_id=patient_session.trace_id,
                session_id=patient_session.session_id,
                icd_codes=soap.icd_codes,
                confidence=soap.confidence,
                escalated=escalated,
                escalation_reason=escalation or "",
                image_captured=bool(patient_session.image_analysis),
                patient_language=patient_session.detected_language or "en",
            )
        )

    # Build transcript from full conversation (patient + assistant turns)
    transcript = (
        patient_session.conversation
        if patient_session.conversation
        else [{"role": "patient", "text": t} for t in patient_session.transcript]
    )

    # Complete case in DB
    soap_dict = {
        "subjective": soap.subjective,
        "objective": soap.objective,
        "assessment": soap.assessment,
        "plan": soap.plan,
        "disclaimer": soap.disclaimer,
    }
    case = await case_repo.complete_case(
        case_id=case.id,
        soap_note=soap_dict,
        icd_codes=soap.icd_codes,
        interview_transcript=transcript,
        escalated=escalated,
    )

    # Discard in-memory session
    bridge.discard(case.id)  # type: ignore[union-attr]

    # Build image list
    images = []
    if case and case.images:
        images = [
            CaseImageResponse(
                id=str(img.id),
                file_path=img.file_path,
                consent_given=img.consent_given,
                rag_results=img.rag_results,
                created_at=img.created_at,
            )
            for img in case.images
        ]

    logger.info(
        "case_completed",
        case_id=case_id,
        escalated=escalated,
        icd_codes=soap.icd_codes,
    )

    return CaseSummaryResponse(
        id=str(case.id),  # type: ignore[union-attr]
        case_number=case.case_number,  # type: ignore[union-attr]
        status=case.status.value,  # type: ignore[union-attr]
        soap_note=soap_dict,
        icd_codes=soap.icd_codes,
        interview_transcript=transcript,
        doctor_notes=case.doctor_notes,  # type: ignore[union-attr]
        escalated=escalated,
        images=images,
    )


@router.get("/{case_id}/summary", response_model=CaseSummaryResponse)
async def get_case_summary(
    case_id: str,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> CaseSummaryResponse:
    """Get the full case summary including SOAP, images, and transcript."""
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    images = [
        CaseImageResponse(
            id=str(img.id),
            file_path=img.file_path,
            consent_given=img.consent_given,
            rag_results=img.rag_results,
            created_at=img.created_at,
        )
        for img in (case.images or [])
    ]

    return CaseSummaryResponse(
        id=str(case.id),
        case_number=case.case_number,
        status=case.status.value,
        soap_note=case.soap_note,
        icd_codes=case.icd_codes,
        interview_transcript=case.interview_transcript,
        doctor_notes=case.doctor_notes,
        escalated=case.escalated,
        images=images,
    )


@router.get("/{case_id}/images/{image_id}")
async def get_case_image(
    case_id: str,
    image_id: str,
    user: User = Depends(require_role("admin", "doctor")),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Serve an uploaded case image file."""
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")

    # Find the image in the case
    target = None
    for img in case.images or []:
        if str(img.id) == image_id:
            target = img
            break

    if target is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Image not found")

    file_path = Path(target.file_path)
    if not file_path.exists():
        raise AppError(code=ErrorCode.NOT_FOUND, message="Image file missing")

    return FileResponse(file_path, media_type="image/jpeg")
