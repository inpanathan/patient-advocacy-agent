"""Base repository with shared session handling."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Base class providing session access to all repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
