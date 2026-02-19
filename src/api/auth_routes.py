"""Authentication API routes: login, refresh, me."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.password import verify_password
from src.auth.tokens import create_access_token, create_refresh_token, decode_token
from src.db.engine import get_session
from src.db.models import User
from src.db.repositories.user_repo import UserRepository
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---- Schemas ----


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    facility_id: str | None


# ---- Endpoints ----


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate with email + password, receive JWT tokens."""
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)

    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(
            code=ErrorCode.AUTH_FAILED,
            message="Invalid email or password",
        )

    if not user.is_active:
        raise AppError(
            code=ErrorCode.AUTH_FAILED,
            message="Account is deactivated",
        )

    logger.info("user_login", user_id=str(user.id), role=user.role.value)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Exchange a refresh token for a new access + refresh token pair."""
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid or expired refresh token",
        ) from None

    if payload.get("type") != "refresh":
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Expected refresh token",
        )

    user_id = uuid.UUID(payload["sub"])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if user is None or not user.is_active:
        raise AppError(
            code=ErrorCode.AUTH_FAILED,
            message="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Get the currently authenticated user's profile."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        facility_id=str(user.facility_id) if user.facility_id else None,
    )
