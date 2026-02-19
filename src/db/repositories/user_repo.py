"""Repository for users and doctor-pool assignments."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import DoctorPool, User, UserRole
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """CRUD operations for users."""

    async def create_user(
        self,
        email: str,
        password_hash: str,
        name: str,
        role: UserRole,
        facility_id: uuid.UUID | None = None,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            role=role,
            facility_id=facility_id,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Look up a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        return await self.session.get(User, user_id)  # type: ignore[no-any-return]

    async def assign_doctor_to_pool(
        self,
        doctor_id: uuid.UUID,
        pool_id: uuid.UUID,
    ) -> DoctorPool:
        """Assign a doctor to a facility pool."""
        dp = DoctorPool(doctor_id=doctor_id, pool_id=pool_id, is_active=True)
        self.session.add(dp)
        await self.session.flush()
        return dp
