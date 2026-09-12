"""
Async SQLAlchemy engine and session factory.
Uses aiosqlite for local development; swap DATABASE_URL in .env for PostgreSQL.

Test isolation (Phase 7): when TEST_DATABASE_URL is set, every engine/session
in this module binds to that isolated SQLite database instead of DATABASE_URL.
The test stack therefore never touches the dev database or production/Neon.
"""
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config.settings import DATABASE_URL, TEST_DATABASE_URL


def _sqlite_file(url: str) -> str | None:
    """Extract the filesystem path from a sqlite(+driver):// URL, or None."""
    if not url.startswith("sqlite"):
        return None
    if ":///" in url:
        return url.split(":///", 1)[1]
    return url.split("://", 1)[1]


def assert_test_url_isolation(test_url: str, production_url: str) -> None:
    """Safety guard for the test stack (raises RuntimeError on violation).

    The isolated test DB must be:
    - an SQLite URL (never PostgreSQL/Neon), and
    - a different database than DATABASE_URL — both by string and by resolved
      file path when both are SQLite file URLs.
    """
    if not test_url.startswith("sqlite"):
        raise RuntimeError(
            "Refusing to run the test stack against a non-SQLite database. "
            "TEST_DATABASE_URL must point at an isolated SQLite temp file."
        )
    if test_url == production_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must not equal DATABASE_URL — tests would run "
            "against the development/production database."
        )
    test_file = _sqlite_file(test_url)
    production_file = _sqlite_file(production_url)
    if test_file and production_file:
        if os.path.abspath(test_file) == os.path.abspath(production_file):
            raise RuntimeError(
                "TEST_DATABASE_URL resolves to the same file as DATABASE_URL — "
                "tests would run against the development/production database."
            )


# Detect the configured dialect. When TEST_DATABASE_URL is set the test stack
# binds here; otherwise the single production/development DATABASE_URL applies.
EFFECTIVE_DATABASE_URL = TEST_DATABASE_URL or DATABASE_URL
IS_TEST = bool(TEST_DATABASE_URL)
IS_SQLITE = EFFECTIVE_DATABASE_URL.startswith("sqlite")

if IS_TEST:
    assert_test_url_isolation(TEST_DATABASE_URL, DATABASE_URL)

TEST_DB_PATH: str | None = None
if IS_TEST:
    TEST_DB_PATH = _sqlite_file(EFFECTIVE_DATABASE_URL)
    parent = os.path.dirname(TEST_DB_PATH)
    if parent and parent != ".":
        os.makedirs(parent, exist_ok=True)

# SQLite-specific options must only apply for SQLite URLs; non-SQLite URLs
# (e.g. Neon/PostgreSQL) keep SQLAlchemy defaults.
engine_kwargs = {
    "echo": False,
    "connect_args": (
        {"check_same_thread": False}
        if IS_SQLITE
        else {"statement_cache_size": 0}
    ),
    # SQLite has no server to ping, so pool_pre_ping is skipped there (default).
    # For PostgreSQL it eagerly discards stale pooled connections.
    "pool_pre_ping": not IS_SQLITE,
}
if IS_TEST:
    # Test sessions may span multiple event loops (pytest) — NullPool creates a
    # fresh connection per session instead of reusing loop-bound connections.
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(EFFECTIVE_DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_TEST_DB_INITIALIZED = False


async def init_db() -> None:
    """Create local-dev tables (SQLite only).

    Local development keeps relying on ``Base.metadata.create_all`` for a
    frictionless first-run experience. Production databases (PostgreSQL/Neon)
    have their schema managed exclusively by Alembic migrations, so this is a
    no-op for non-SQLite URLs — application startup never mutates production
    schema.

    Test mode (``TEST_DATABASE_URL`` set): the first call per process performs
    one pristine reset — ``drop_all`` + ``create_all`` + the canonical seed —
    so every test run starts clean. Re-entrant calls (e.g. the app lifespan)
    are no-ops and never wipe in-progress test data.
    """
    global _TEST_DB_INITIALIZED
    if not IS_SQLITE:
        return

    # Import models so SQLAlchemy registers them before create_all
    import models.flight    # noqa: F401
    import models.user      # noqa: F401
    import models.booking   # noqa: F401

    if IS_TEST:
        if _TEST_DB_INITIALIZED:
            return
        await reset_test_db()
        _TEST_DB_INITIALIZED = True
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_test_db() -> dict[str, int]:
    """Rebuild (drop_all + create_all + canonical seed) the isolated test DB.

    Only valid when ``TEST_DATABASE_URL`` is set. Pytest calls this once at
    session start; standalone test runners get the same effect through the
    first ``init_db()`` call in their process.
    """
    if not IS_TEST:
        raise RuntimeError("reset_test_db() is only valid when TEST_DATABASE_URL is set")

    # Import models so SQLAlchemy registers them before create_all
    import models.flight    # noqa: F401
    import models.user      # noqa: F401
    import models.booking   # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from database.seed import seed_database

    async with AsyncSessionLocal() as session:
        counts = await seed_database(session)
    return counts