"""Repository for facility pools and facilities."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import Facility, FacilityPool
from src.db.repositories.base import BaseRepository


class FacilityRepository(BaseRepository):
    """CRUD operations for facility pools and facilities."""

    async def create_pool(
        self,
        pool_code: str,
        name: str,
        region: str,
    ) -> FacilityPool:
        """Create a new facility pool."""
        pool = FacilityPool(pool_code=pool_code, name=name, region=region)
        self.session.add(pool)
        await self.session.flush()
        return pool

    async def get_pool(self, pool_id: uuid.UUID) -> FacilityPool | None:
        """Get a facility pool by ID."""
        return await self.session.get(FacilityPool, pool_id)  # type: ignore[no-any-return]

    async def create_facility(
        self,
        pool_id: uuid.UUID,
        facility_code: str,
        name: str,
        location: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Facility:
        """Create a new facility in a pool."""
        facility = Facility(
            pool_id=pool_id,
            facility_code=facility_code,
            name=name,
            location=location,
            latitude=latitude,
            longitude=longitude,
        )
        self.session.add(facility)
        await self.session.flush()
        return facility

    async def get_facility(self, facility_id: uuid.UUID) -> Facility | None:
        """Get a facility by ID."""
        return await self.session.get(Facility, facility_id)  # type: ignore[no-any-return]

    async def list_facilities(self, pool_id: uuid.UUID | None = None) -> list[Facility]:
        """List facilities, optionally filtered by pool."""
        stmt = select(Facility).where(Facility.is_active.is_(True))
        if pool_id is not None:
            stmt = stmt.where(Facility.pool_id == pool_id)
        stmt = stmt.order_by(Facility.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
