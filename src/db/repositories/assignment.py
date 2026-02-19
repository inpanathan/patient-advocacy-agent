"""Doctor assignment via pool-based least-loaded algorithm."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, text

from src.db.models import Case, CaseStatus, DoctorPool, Facility, User, UserRole
from src.db.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository):
    """Assigns doctors to cases based on pool membership and current load."""

    async def assign_least_loaded_doctor(
        self,
        facility_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """Find the least-loaded active doctor in the facility's pool.

        Returns the doctor's user ID or None if no doctors are available.
        Uses a single query with LEFT JOIN, GROUP BY, and ORDER BY.
        """
        # Subquery: count open cases per doctor
        open_statuses = [CaseStatus.awaiting_review.value, CaseStatus.under_review.value]

        stmt = (
            select(
                User.id,
                func.count(Case.id).filter(Case.status.in_(open_statuses)).label("load"),
            )
            .select_from(User)
            .join(DoctorPool, DoctorPool.doctor_id == User.id)
            .join(Facility, Facility.pool_id == DoctorPool.pool_id)
            .outerjoin(Case, Case.doctor_id == User.id)
            .where(
                Facility.id == facility_id,
                User.role == UserRole.doctor,
                User.is_active.is_(True),
                DoctorPool.is_active.is_(True),
            )
            .group_by(User.id, User.created_at)
            .order_by(text("load ASC"), User.created_at.asc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row[0]  # type: ignore[no-any-return]
