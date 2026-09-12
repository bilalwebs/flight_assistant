"""Alembic migration environment for the async SQLAlchemy architecture.

The database URL is read from the project's single source of truth
(config.settings.DATABASE_URL) which supports both:
  - sqlite+aiosqlite:///./flight_assistant.db   (local development)
  - postgresql+asyncpg://...                     (production / Neon)

Environment variables override the .env file in python-decouple, so operators
can point Alembic at a target database without editing any file:
  $env:DATABASE_URL = "sqlite+aiosqlite:///./scratch.db"   (Windows PowerShell)
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from config.settings import DATABASE_URL
from database.database import Base

# Import the model modules so their metadata is registered on Base.metadata,
# which is what autogenerate diffing uses as the source of truth.
import models.flight        # noqa: F401
import models.user          # noqa: F401
import models.booking       # noqa: F401

config = context.config

# Pull the URL from the project configuration rather than alembic.ini.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' (SQL script) mode — no connection needed."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations, disposing afterwards."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against the configured async driver."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()