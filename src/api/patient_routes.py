"""Patient management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import CreatePatientRequest, PatientResponse
from src.auth.dependencies import require_role
from src.db.engine import get_session
from src.db.models import Sex, User
from src.db.repositories.patient_repo import PatientRepository
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/", response_model=PatientResponse)
async def create_patient(
    body: CreatePatientRequest,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> PatientResponse:
    """Register a new patient (admin only)."""
    repo = PatientRepository(session)
    facility_id = uuid.UUID(body.facility_id)
    patient_number = await repo.generate_patient_number(facility_id)

    try:
        sex = Sex(body.sex)
    except ValueError:
        sex = Sex.unknown

    patient = await repo.create_patient(
        facility_id=facility_id,
        patient_number=patient_number,
        age_range=body.age_range,
        sex=sex,
        language=body.language,
    )
    logger.info("patient_created", patient_id=str(patient.id), number=patient.patient_number)
    return PatientResponse(
        id=str(patient.id),
        facility_id=str(patient.facility_id),
        patient_number=patient.patient_number,
        age_range=patient.age_range,
        sex=patient.sex.value,
        language=patient.language,
        created_at=patient.created_at,
    )


@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    facility_id: str,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[PatientResponse]:
    """List patients at a facility (admin only)."""
    repo = PatientRepository(session)
    patients = await repo.list_patients(uuid.UUID(facility_id))
    return [
        PatientResponse(
            id=str(p.id),
            facility_id=str(p.facility_id),
            patient_number=p.patient_number,
            age_range=p.age_range,
            sex=p.sex.value,
            language=p.language,
            created_at=p.created_at,
        )
        for p in patients
    ]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> PatientResponse:
    """Get a patient by ID (admin only)."""
    repo = PatientRepository(session)
    patient = await repo.get_patient(uuid.UUID(patient_id))
    if patient is None:
        raise AppError(code=ErrorCode.NOT_FOUND, message="Patient not found")
    return PatientResponse(
        id=str(patient.id),
        facility_id=str(patient.facility_id),
        patient_number=patient.patient_number,
        age_range=patient.age_range,
        sex=patient.sex.value,
        language=patient.language,
        created_at=patient.created_at,
    )
