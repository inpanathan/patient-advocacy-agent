"""Facility and facility pool management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateFacilityPoolRequest,
    CreateFacilityRequest,
    FacilityPoolResponse,
    FacilityResponse,
)
from src.auth.dependencies import require_role
from src.db.engine import get_session
from src.db.models import User
from src.db.repositories.facility_repo import FacilityRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.post("/pools", response_model=FacilityPoolResponse)
async def create_pool(
    body: CreateFacilityPoolRequest,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> FacilityPoolResponse:
    """Create a new facility pool (admin only)."""
    repo = FacilityRepository(session)
    pool = await repo.create_pool(
        pool_code=body.pool_code,
        name=body.name,
        region=body.region,
    )
    logger.info("facility_pool_created", pool_id=str(pool.id), pool_code=pool.pool_code)
    return FacilityPoolResponse(
        id=str(pool.id),
        pool_code=pool.pool_code,
        name=pool.name,
        region=pool.region,
    )


@router.post("/", response_model=FacilityResponse)
async def create_facility(
    body: CreateFacilityRequest,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> FacilityResponse:
    """Create a new facility (admin only)."""
    repo = FacilityRepository(session)
    facility = await repo.create_facility(
        pool_id=uuid.UUID(body.pool_id),
        facility_code=body.facility_code,
        name=body.name,
        location=body.location,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    logger.info("facility_created", facility_id=str(facility.id))
    return FacilityResponse(
        id=str(facility.id),
        pool_id=str(facility.pool_id),
        facility_code=facility.facility_code,
        name=facility.name,
        location=facility.location,
        latitude=facility.latitude,
        longitude=facility.longitude,
    )


@router.get("/", response_model=list[FacilityResponse])
async def list_facilities(
    pool_id: str | None = None,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[FacilityResponse]:
    """List all active facilities (admin only)."""
    repo = FacilityRepository(session)
    pid = uuid.UUID(pool_id) if pool_id else None
    facilities = await repo.list_facilities(pool_id=pid)
    return [
        FacilityResponse(
            id=str(f.id),
            pool_id=str(f.pool_id),
            facility_code=f.facility_code,
            name=f.name,
            location=f.location,
            latitude=f.latitude,
            longitude=f.longitude,
        )
        for f in facilities
    ]
