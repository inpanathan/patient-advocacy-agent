"""FastAPI dependencies for authentication and role-based access control."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import decode_token
from src.db.engine import get_session
from src.db.models import User
from src.db.repositories.user_repo import UserRepository
from src.utils.errors import AppError, ErrorCode

_bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Decode JWT and load the user from the database.

    Raises AppError with appropriate codes on failure.
    """
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid or expired token",
        ) from None

    token_type = payload.get("type")
    if token_type != "access":
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Expected access token",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Token missing subject",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppError(
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid user ID in token",
        ) from None

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError(
            code=ErrorCode.AUTH_FAILED,
            message="User not found or inactive",
        )

    return user


def require_role(
    *roles: str,
) -> Callable[..., Coroutine[Any, Any, User]]:
    """Factory that returns a dependency requiring the user to have one of the given roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    """

    async def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise AppError(
                code=ErrorCode.FORBIDDEN,
                message=f"Role '{user.role.value}' not authorized. Required: {', '.join(roles)}",
            )
        return user

    return _check_role
