"""Password hashing and verification using bcrypt."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    result: bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return result.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    result: bool = bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    return result
