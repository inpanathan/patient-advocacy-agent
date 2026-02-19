"""Case lifecycle endpoints for admins (patient mode)."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
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
from src.db.models import AudioRole, User
from src.db.repositories.assignment import AssignmentRepository
from src.db.repositories.case_repo import CaseRepository
from src.models.rag_retrieval import RAGRetriever
from src.models.stt import get_stt_service
from src.models.tts import get_tts_service
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

    # RAG retrieval
    rag_results_data: dict | None = None
    retriever = _get_retriever(request)
    if retriever:
        try:
            rag_response = retriever.query_by_image(str(image_path))
            rag_results_data = {
                "results": [
                    {"diagnosis": r.diagnosis, "icd_code": r.icd_code, "score": round(r.score, 4)}
                    for r in rag_response.results[:5]
                ]
            }
        except Exception as exc:
            logger.warning("case_image_rag_failed", case_id=case_id, error=str(exc))

    # Save to DB
    db_image = await case_repo.add_image(
        case_id=case.id,
        file_path=str(image_path),
        consent_given=True,
        rag_results=rag_results_data,
    )

    return {
        "image_id": str(db_image.id),
        "rag_results": rag_results_data,
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
    retriever = _get_retriever(request)
    rag_results = None
    if retriever and patient_session.transcript:
        try:
            text_query = " ".join(patient_session.transcript)
            rag_results = retriever.query_by_text(text_query)
        except Exception as exc:
            logger.warning("complete_rag_failed", case_id=case_id, error=str(exc))

    soap = await generate_soap_note(
        patient_session,
        rag_results=rag_results,
        image_analysis=patient_session.image_analysis,
    )

    # Check escalation
    escalation = _interview_agent.check_escalation(f"{soap.assessment} {soap.plan}")
    escalated = bool(escalation)

    # Build transcript
    transcript = [{"role": "transcript", "text": t} for t in patient_session.transcript]

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
