"""
Phase 7 — Database Testing & Isolation.

Five pytest tests proving tests never run against the dev/production database:
1. The test DB is a distinct SQLite temp file (and the guard rejects non-SQLite
   URLs, prod-equal URLs, and same-resolved-file URLs).
2. A fresh isolated test DB starts clean (empty after create_all).
3. Data written to the test DB never leaks into a dev-like database.
4. HTTP endpoints (via FastAPI dependency override) write to the test DB.
5. Cleanup removes the temp DB file(s) and its temp directory.
"""
import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from database.database import Base  # noqa: E402  (import before models: models import this module)
import models.booking  # noqa: F401, E402  (register tables on Base.metadata)
import models.flight  # noqa: F401, E402
import models.user  # noqa: F401, E402
from tests.isolation import cleanup_db_files, cleanup_temp_dir, make_test_url, sqlite_file_path


async def _fresh_engine(url: str):
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _count_users_in(url: str, email: str) -> int:
    from sqlalchemy import func, select
    from models.user import User

    engine = await _fresh_engine(url)
    try:
        async with engine.connect() as conn:
            return (
                await conn.execute(
                    select(func.count()).select_from(User).where(User.email == email)
                )
            ).scalar_one()
    finally:
        await engine.dispose()


async def _insert_user(url: str, email: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from models.user import User

    engine = await _fresh_engine(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            session.add(User(id=str(uuid.uuid4()), email=email, name="Probe"))
            await session.commit()
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# 1. Test DB is NOT the dev/production DB
# ---------------------------------------------------------------------------

def test_1_test_db_is_not_dev_db():
    from config import settings
    from database.database import (
        EFFECTIVE_DATABASE_URL,
        assert_test_url_isolation,
    )

    assert EFFECTIVE_DATABASE_URL.startswith("sqlite"), "test DB must be SQLite"
    assert EFFECTIVE_DATABASE_URL != settings.DATABASE_URL, "test DB deviates from dev/prod URL"

    # By resolved file path, when both are SQLite files.
    test_file = os.path.abspath(sqlite_file_path(EFFECTIVE_DATABASE_URL))
    if settings.DATABASE_URL.startswith("sqlite"):
        dev_file = os.path.abspath(sqlite_file_path(settings.DATABASE_URL))
        assert test_file != dev_file, "test DB file must differ from dev DB file"
        assert os.path.basename(test_file) != "flight_assistant.db"

    # The safety guard rejects non-SQLite (e.g. Neon) targets.
    with pytest.raises(RuntimeError):
        assert_test_url_isolation(
            "postgresql://user:pass@host:5432/prod?sslmode=require",
            "postgresql://user:pass@host:5432/prod?sslmode=require",
        )
    # ... rejects TEST == DATABASE_URL.
    with pytest.raises(RuntimeError):
        assert_test_url_isolation(
            "sqlite+aiosqlite:///./flight_assistant.db",
            "sqlite+aiosqlite:///./flight_assistant.db",
        )
    # ... rejects same resolved file under a different spelling.
    with pytest.raises(RuntimeError):
        assert_test_url_isolation(
            f"sqlite+aiosqlite:///{os.path.abspath('./flight_assistant.db')}",
            "sqlite+aiosqlite:///./flight_assistant.db",
        )


# ---------------------------------------------------------------------------
# 2. Fresh isolated test DB starts clean
# ---------------------------------------------------------------------------

def test_2_test_db_starts_clean():
    from sqlalchemy import func, select
    from models.flight import Flight
    from models.user import User

    url, root = make_test_url()

    async def _probe():
        engine = await _fresh_engine(url)
        try:
            async with engine.connect() as conn:
                flights = (
                    await conn.execute(select(func.count()).select_from(Flight))
                ).scalar_one()
                users = (
                    await conn.execute(select(func.count()).select_from(User))
                ).scalar_one()
                return flights, users
        finally:
            await engine.dispose()

    flights, users = asyncio.run(_probe())
    assert flights == 0, "fresh test DB must start with zero flights"
    assert users == 0, "fresh test DB must start with zero users"
    cleanup_temp_dir(root)


# ---------------------------------------------------------------------------
# 3. No data leak between test DB and a dev-like DB
# ---------------------------------------------------------------------------

def test_3_no_data_leak_between_dbs():
    url_test, root_test = make_test_url()
    url_dev_like, root_dev_like = make_test_url()
    marker = f"leak_{uuid.uuid4().hex[:8]}@example.com"

    asyncio.run(_insert_user(url_test, marker))

    in_test = asyncio.run(_count_users_in(url_test, marker))
    in_dev_like = asyncio.run(_count_users_in(url_dev_like, marker))

    assert in_test == 1, "marker user must live in the test DB"
    assert in_dev_like == 0, "marker user must NOT appear in a dev-like DB"

    cleanup_temp_dir(root_test)
    cleanup_temp_dir(root_dev_like)


# ---------------------------------------------------------------------------
# 4. HTTP endpoints write to the test DB (dependency override active)
# ---------------------------------------------------------------------------

def test_4_http_uses_test_db():
    from database.database import EFFECTIVE_DATABASE_URL, get_db
    from main import app

    assert app.dependency_overrides.get(get_db) is not None, "get_db override must be installed"

    client = TestClient(app)
    email = f"http_iso_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecurePass123", "name": "Iso"},
    )
    assert r.status_code == 201, r.text

    in_test = asyncio.run(_count_users_in(EFFECTIVE_DATABASE_URL, email))

    blank_url, blank_root = make_test_url()
    in_blank = asyncio.run(_count_users_in(blank_url, email))
    cleanup_temp_dir(blank_root)

    assert in_test == 1, "HTTP-registered user must land in the test DB"
    assert in_blank == 0, "HTTP-registered user must NOT land in another DB"


# ---------------------------------------------------------------------------
# 5. Cleanup removes the temp DB and its temp directory
# ---------------------------------------------------------------------------

def test_5_cleanup_removes_temp_db():
    url, root = make_test_url()
    primary = sqlite_file_path(url)

    for suffix in ("", "-wal", "-shm"):
        with open(primary + suffix, "w") as fh:
            fh.write("x")
    assert os.path.exists(primary), "precondition: temp DB file exists"

    cleanup_db_files(primary)
    assert not os.path.exists(primary), "temp DB file removed"
    assert not os.path.exists(primary + "-wal"), "WAL sidecar removed"
    assert not os.path.exists(primary + "-shm"), "SHM sidecar removed"

    cleanup_temp_dir(root)
    assert not os.path.exists(root), "temp directory removed"