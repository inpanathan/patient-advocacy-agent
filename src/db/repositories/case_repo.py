"""Repository for clinical cases, images, and audio."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from src.db.models import (
    AudioRole,
    Case,
    CaseAudio,
    CaseImage,
    CaseStatus,
)
from src.db.repositories.base import BaseRepository


class CaseRepository(BaseRepository):
    """CRUD operations for cases and associated media."""

    async def create_case(
        self,
        case_number: str,
        facility_id: uuid.UUID,
        patient_id: uuid.UUID,
        admin_id: uuid.UUID,
        doctor_id: uuid.UUID | None = None,
    ) -> Case:
        """Create a new clinical case."""
        case = Case(
            case_number=case_number,
            facility_id=facility_id,
            patient_id=patient_id,
            admin_id=admin_id,
            doctor_id=doctor_id,
            status=CaseStatus.in_progress,
        )
        self.session.add(case)
        await self.session.flush()
        return case

    async def get_case(self, case_id: uuid.UUID) -> Case | None:
        """Get a case by ID."""
        return await self.session.get(Case, case_id)  # type: ignore[no-any-return]

    async def update_case(
        self,
        case_id: uuid.UUID,
        **kwargs: Any,
    ) -> Case | None:
        """Update case fields."""
        case: Case | None = await self.session.get(Case, case_id)
        if case is None:
            return None
        for key, value in kwargs.items():
            if hasattr(case, key):
                setattr(case, key, value)
        await self.session.flush()
        return case

    async def complete_case(
        self,
        case_id: uuid.UUID,
        soap_note: dict[str, Any] | None = None,
        icd_codes: list[str] | None = None,
        interview_transcript: list[dict[str, Any]] | None = None,
        escalated: bool = False,
    ) -> Case | None:
        """Finalize a case with SOAP data and mark it awaiting review."""
        case: Case | None = await self.session.get(Case, case_id)
        if case is None:
            return None
        case.soap_note = soap_note
        case.icd_codes = icd_codes
        case.interview_transcript = interview_transcript
        case.escalated = escalated
        case.status = CaseStatus.escalated if escalated else CaseStatus.awaiting_review
        await self.session.flush()
        return case

    async def list_doctor_cases(
        self,
        doctor_id: uuid.UUID,
        status: CaseStatus | None = None,
    ) -> list[Case]:
        """List cases assigned to a doctor, optionally filtered by status."""
        stmt = select(Case).where(Case.doctor_id == doctor_id)
        if status is not None:
            stmt = stmt.where(Case.status == status)
        stmt = stmt.order_by(Case.escalated.desc(), Case.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_image(
        self,
        case_id: uuid.UUID,
        file_path: str,
        consent_given: bool = False,
        rag_results: dict[str, Any] | None = None,
    ) -> CaseImage:
        """Attach an image to a case."""
        image = CaseImage(
            case_id=case_id,
            file_path=file_path,
            consent_given=consent_given,
            rag_results=rag_results,
        )
        self.session.add(image)
        await self.session.flush()
        return image

    async def add_audio(
        self,
        case_id: uuid.UUID,
        role: AudioRole,
        transcript: str | None = None,
        file_path: str | None = None,
        duration_ms: int | None = None,
    ) -> CaseAudio:
        """Attach an audio segment to a case."""
        audio = CaseAudio(
            case_id=case_id,
            role=role,
            transcript=transcript,
            file_path=file_path,
            duration_ms=duration_ms,
        )
        self.session.add(audio)
        await self.session.flush()
        return audio

    async def generate_case_number(self, facility_id: uuid.UUID) -> str:
        """Generate the next case number for a facility (CASE-YYYYMMDD-NNNN)."""
        today = datetime.now(UTC).strftime("%Y%m%d")
        prefix = f"CASE-{today}-"
        stmt = (
            select(func.count())
            .select_from(Case)
            .where(Case.facility_id == facility_id)
            .where(Case.case_number.like(f"{prefix}%"))
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return f"{prefix}{count + 1:04d}"
