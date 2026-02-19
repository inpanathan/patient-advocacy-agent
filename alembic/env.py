"""Alembic environment configuration.

Imports Base.metadata from ORM models and uses settings.database.sync_url
for the connection string.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context  # type: ignore[attr-defined]
from src.db.models import Base  # noqa: F401 — registers all models
from src.utils.config import settings

config = context.config

# Override sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.database.sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
