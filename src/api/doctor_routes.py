"""Doctor-facing endpoints for case review and management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CaseImageResponse,
    CaseSummaryResponse,
    DoctorCaseResponse,
    DoctorCompleteRequest,
    DoctorNotesRequest,
)
from src.auth.dependencies import require_role
from src.db.engine import get_session
from src.db.models import CaseStatus, User
from src.db.repositories.case_repo import CaseRepository
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/doctor", tags=["doctor"])


@router.get("/cases", response_model=list[DoctorCaseResponse])
async def list_my_cases(
    status: str | None = None,
    user: User = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
) -> list[DoctorCaseResponse]:
    """List cases assigned to the authenticated doctor."""
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

    cases = await case_repo.list_doctor_cases(user.id, status=filter_status)
    return [
        DoctorCaseResponse(
            id=str(c.id),
            case_number=c.case_number,
            patient_id=str(c.patient_id),
            facility_id=str(c.facility_id),
            status=c.status.value,
            escalated=c.escalated,
            soap_note=c.soap_note,
            icd_codes=c.icd_codes,
            doctor_notes=c.doctor_notes,
            created_at=c.created_at,
        )
        for c in cases
    ]


@router.put("/cases/{case_id}/review")
async def start_review(
    case_id: str,
    user: User = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Mark a case as under review by this doctor."""
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")
    if case.doctor_id != user.id:
        raise AppError(code=ErrorCode.FORBIDDEN, message="Not assigned to this case")

    case = await case_repo.update_case(case.id, status=CaseStatus.under_review)
    logger.info("case_review_started", case_id=case_id, doctor_id=str(user.id))
    return {"status": "under_review"}


@router.put("/cases/{case_id}/notes")
async def update_notes(
    case_id: str,
    body: DoctorNotesRequest,
    user: User = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Add or update doctor notes on a case."""
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")
    if case.doctor_id != user.id:
        raise AppError(code=ErrorCode.FORBIDDEN, message="Not assigned to this case")

    await case_repo.update_case(case.id, doctor_notes=body.notes)
    logger.info("doctor_notes_updated", case_id=case_id)
    return {"notes": body.notes}


@router.put("/cases/{case_id}/complete", response_model=CaseSummaryResponse)
async def doctor_complete_case(
    case_id: str,
    body: DoctorCompleteRequest,
    user: User = Depends(require_role("doctor")),
    session: AsyncSession = Depends(get_session),
) -> CaseSummaryResponse:
    """Doctor completes review of a case."""
    case_repo = CaseRepository(session)
    case = await case_repo.get_case(uuid.UUID(case_id))
    if case is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Case not found")
    if case.doctor_id != user.id:
        raise AppError(code=ErrorCode.FORBIDDEN, message="Not assigned to this case")

    updates: dict = {"status": CaseStatus.completed}
    if body.notes is not None:
        updates["doctor_notes"] = body.notes
    if body.final_icd_codes is not None:
        updates["icd_codes"] = body.final_icd_codes

    case = await case_repo.update_case(case.id, **updates)

    images = [
        CaseImageResponse(
            id=str(img.id),
            file_path=img.file_path,
            consent_given=img.consent_given,
            rag_results=img.rag_results,
            created_at=img.created_at,
        )
        for img in (case.images if case else [])  # type: ignore[union-attr]
    ]

    logger.info("doctor_case_completed", case_id=case_id, doctor_id=str(user.id))

    return CaseSummaryResponse(
        id=str(case.id),  # type: ignore[union-attr]
        case_number=case.case_number,  # type: ignore[union-attr]
        status=case.status.value,  # type: ignore[union-attr]
        soap_note=case.soap_note,  # type: ignore[union-attr]
        icd_codes=case.icd_codes,  # type: ignore[union-attr]
        interview_transcript=case.interview_transcript,  # type: ignore[union-attr]
        doctor_notes=case.doctor_notes,  # type: ignore[union-attr]
        escalated=case.escalated,  # type: ignore[union-attr]
        images=images,
    )
