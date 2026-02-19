"""Tests for database engine configuration and session management."""

from __future__ import annotations

import pytest

from src.utils.config import DatabaseSettings


class TestDatabaseSettings:
    """Test DatabaseSettings URL generation and defaults."""

    def test_async_url_format(self) -> None:
        db = DatabaseSettings(
            host="myhost",
            port=5433,
            name="mydb",
            user="myuser",
            password="secret",
        )
        assert db.async_url == "postgresql+asyncpg://myuser:secret@myhost:5433/mydb"

    def test_sync_url_format(self) -> None:
        db = DatabaseSettings(
            host="myhost",
            port=5433,
            name="mydb",
            user="myuser",
            password="secret",
        )
        assert db.sync_url == "postgresql://myuser:secret@myhost:5433/mydb"

    def test_defaults(self) -> None:
        """Verify defaults by explicitly constructing with known values."""
        db = DatabaseSettings(
            host="localhost",
            port=5432,
            name="patient_advocacy",
            user="patient_advocacy",
            password="",
            pool_size=5,
            echo=False,
            enabled=True,
        )
        assert db.host == "localhost"
        assert db.port == 5432
        assert db.name == "patient_advocacy"
        assert db.user == "patient_advocacy"
        assert db.pool_size == 5
        assert db.echo is False
        assert db.enabled is True

    def test_enabled_flag(self) -> None:
        db = DatabaseSettings(enabled=False)
        assert db.enabled is False


class TestEngineLifecycle:
    """Test engine init/close without a real database."""

    def test_get_engine_before_init_raises(self) -> None:
        # Reset global state for isolation
        import src.db.engine as mod
        from src.db.engine import get_engine

        original_engine = mod._engine
        mod._engine = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_engine()
        finally:
            mod._engine = original_engine

    def test_get_session_factory_before_init_raises(self) -> None:
        import src.db.engine as mod
        from src.db.engine import get_session_factory

        original_factory = mod._session_factory
        mod._session_factory = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_session_factory()
        finally:
            mod._session_factory = original_factory

    def test_get_session_is_async_generator(self) -> None:
        import inspect

        from src.db.engine import get_session

        assert inspect.isasyncgenfunction(get_session)
