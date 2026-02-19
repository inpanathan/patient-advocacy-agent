"""Repository for patient records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from src.db.models import Patient, Sex
from src.db.repositories.base import BaseRepository


class PatientRepository(BaseRepository):
    """CRUD operations for patients."""

    async def create_patient(
        self,
        facility_id: uuid.UUID,
        patient_number: str,
        age_range: str | None = None,
        sex: Sex = Sex.unknown,
        language: str = "en",
    ) -> Patient:
        """Create a new patient record."""
        patient = Patient(
            facility_id=facility_id,
            patient_number=patient_number,
            age_range=age_range,
            sex=sex,
            language=language,
        )
        self.session.add(patient)
        await self.session.flush()
        return patient

    async def get_patient(self, patient_id: uuid.UUID) -> Patient | None:
        """Get a patient by ID."""
        return await self.session.get(Patient, patient_id)  # type: ignore[no-any-return]

    async def list_patients(self, facility_id: uuid.UUID) -> list[Patient]:
        """List patients at a facility."""
        stmt = (
            select(Patient)
            .where(Patient.facility_id == facility_id)
            .order_by(Patient.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def generate_patient_number(self, facility_id: uuid.UUID) -> str:
        """Generate the next patient number for a facility (PAT-YYYYMMDD-NNNN)."""
        today = datetime.now(UTC).strftime("%Y%m%d")
        prefix = f"PAT-{today}-"
        stmt = (
            select(func.count())
            .select_from(Patient)
            .where(Patient.facility_id == facility_id)
            .where(Patient.patient_number.like(f"{prefix}%"))
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return f"{prefix}{count + 1:04d}"
