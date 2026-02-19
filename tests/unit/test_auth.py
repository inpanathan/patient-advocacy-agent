"""Tests for password hashing, JWT tokens, and error codes."""

from __future__ import annotations

import uuid

import pytest

from src.auth.password import hash_password, verify_password
from src.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.utils.errors import ErrorCode


class TestPassword:
    """Password hashing and verification."""

    def test_hash_and_verify(self) -> None:
        plain = "s3cur3P@ss"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestTokens:
    """JWT access and refresh token creation/verification."""

    def test_create_and_decode_access_token(self) -> None:
        uid = uuid.uuid4()
        token = create_access_token(uid, "admin")
        payload = decode_token(token)
        assert payload["sub"] == str(uid)
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self) -> None:
        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        payload = decode_token(token)
        assert payload["sub"] == str(uid)
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_invalid_token_raises(self) -> None:
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")


class TestAuthErrorCodes:
    """Verify auth error codes exist."""

    def test_error_codes_exist(self) -> None:
        assert ErrorCode.AUTH_FAILED == "AUTH_FAILED"
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"
        assert ErrorCode.TOKEN_EXPIRED == "TOKEN_EXPIRED"
        assert ErrorCode.TOKEN_INVALID == "TOKEN_INVALID"
