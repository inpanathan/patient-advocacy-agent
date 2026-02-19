"""Async database engine and session management.

Provides:
- Async SQLAlchemy engine with connection pooling
- Async session factory for use in repositories
- FastAPI dependency for request-scoped sessions
- Lifecycle functions for app startup/shutdown
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the global async engine. Raises if not initialized."""
    if _engine is None:
        msg = "Database engine not initialized. Call init_db() first."
        raise RuntimeError(msg)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global session factory. Raises if not initialized."""
    if _session_factory is None:
        msg = "Database session factory not initialized. Call init_db() first."
        raise RuntimeError(msg)
    return _session_factory


async def init_db() -> None:
    """Initialize the async engine and session factory."""
    global _engine, _session_factory  # noqa: PLW0603

    db_cfg = settings.database
    _engine = create_async_engine(
        db_cfg.async_url,
        pool_size=db_cfg.pool_size,
        echo=db_cfg.echo,
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
    )
    logger.info(
        "db_initialized",
        host=db_cfg.host,
        port=db_cfg.port,
        database=db_cfg.name,
        pool_size=db_cfg.pool_size,
    )


async def close_db() -> None:
    """Dispose engine and release all connections."""
    global _engine, _session_factory  # noqa: PLW0603

    if _engine is not None:
        await _engine.dispose()
        logger.info("db_closed")
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped async session.

    Usage:
        @router.get("/items")
        async def list_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
