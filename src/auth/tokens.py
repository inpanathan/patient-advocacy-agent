"""JWT token creation and verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from src.utils.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Create a JWT access token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    result: str = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return result


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a JWT refresh token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
    }
    result: str = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return result


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the payload dict.
    Raises JWTError if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise
    return payload  # type: ignore[no-any-return]
