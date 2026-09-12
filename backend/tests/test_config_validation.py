"""
Phase 8 — Production Configuration Validation.

Verifies the environment-separation and fail-fast guards without touching the
real Neon database. All values used for production simulation are FAKE
placeholders; no real credentials appear anywhere in this file.

  A. Production configuration with a PostgreSQL URL is accepted.
  B. Production configuration does not use the test database.
  C. Production requires secure JWT configuration (fail fast).
  D. Production CORS does not silently become unrestricted.
  E. SQLite development configuration still works (and never auto-seeds).
  F. Phase 7 test isolation remains functional after Phase 8 changes.
  G. Alembic resolves the configured production database URL without
     exposing any secret.
"""
import os
import subprocess
import sys

import pytest

from config import settings
from database.database import (
    EFFECTIVE_DATABASE_URL,
    IS_SQLITE,
    IS_TEST,
    assert_test_url_isolation,
)

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Test A — production PostgreSQL URL accepted ──────────────────────────────
def test_a_production_postgresql_url_accepted():
    normalized = settings.normalize_database_url(
        "postgresql://app:fake-secret@db.example:5432/flightdb?sslmode=require"
    )
    assert normalized == "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb"

    psycopg2_style = settings.normalize_database_url(
        "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb"
        "?sslmode=require&channel_binding=require&application_name=api"
    )
    assert psycopg2_style == \
        "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb?application_name=api"

    # Production validation accepts the normalized PostgreSQL+asyncpg URL.
    assert settings.validate_production_db_url(normalized, "") is None


# ── Test B — production does not use the test database ───────────────────────
def test_b_production_does_not_use_test_db():
    # SQLite is a development/testing database, never a production one.
    with pytest.raises(RuntimeError):
        settings.validate_production_db_url(
            "sqlite+aiosqlite:///./flight_assistant.db", ""
        )

    # Production must never equal the test database URL.
    prod = "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb"
    with pytest.raises(RuntimeError):
        settings.validate_production_db_url(prod, prod)

    # Live Phase 7 stack: the effective (test) DB is SQLite and differs from
    # the configured production URL.
    assert IS_TEST and IS_SQLITE
    assert EFFECTIVE_DATABASE_URL != settings.DATABASE_URL
    assert EFFECTIVE_DATABASE_URL.startswith("sqlite+aiosqlite:///")
    if settings.DATABASE_URL.startswith("postgres"):
        assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")


# ── Test C — production requires secure JWT configuration ────────────────────
def test_c_production_requires_secure_jwt():
    for weak in (
        "",
        "your-secret-key-change-in-production",
        "replace-with-a-long-random-secret",
        "changeme",
        "short-secret",
    ):
        with pytest.raises(RuntimeError):
            settings.validate_jwt_secret(weak, "production")

    # A genuinely strong secret passes...
    assert settings.validate_jwt_secret("x" * 48, "production") is None
    # ...while local development keeps the permissive default.
    assert settings.validate_jwt_secret("", "development") is None


# ── Test D — production CORS must not be unrestricted ────────────────────────
def test_d_production_cors_not_unrestricted():
    for origins in (["*"], ["http://a.example", "*"], [], [""]):
        with pytest.raises(RuntimeError):
            settings.validate_cors_origins(origins, "production")

    assert settings.validate_cors_origins(["https://app.example"], "production") is None
    assert settings.validate_cors_origins(["http://localhost:3000"], "development") is None


# ── Test E — SQLite development configuration still works ────────────────────
def test_e_sqlite_dev_configuration_works(tmp_path):
    dev_db = (tmp_path / "dev.db").as_posix()
    env = os.environ.copy()
    env["ENVIRONMENT"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{dev_db}"
    env.pop("TEST_DATABASE_URL", None)  # pure dev mode — no test override

    code = (
        "import asyncio\n"
        "from sqlalchemy import func, select\n"
        "from config.settings import DATABASE_URL, TEST_DATABASE_URL, ENVIRONMENT, IS_PRODUCTION\n"
        "from database.database import IS_SQLITE, IS_TEST, init_db, AsyncSessionLocal\n"
        "from models.flight import Flight\n"
        "assert ENVIRONMENT == 'development' and not IS_PRODUCTION\n"
        "assert DATABASE_URL.startswith('sqlite+aiosqlite:///') and TEST_DATABASE_URL == ''\n"
        "assert IS_SQLITE and not IS_TEST\n"
        "asyncio.run(init_db())\n"
        "async def flights_count():\n"
        "    async with AsyncSessionLocal() as s:\n"
        "        return (await s.execute(select(func.count()).select_from(Flight))).scalar_one()\n"
        "n = asyncio.run(flights_count())\n"
        "assert n == 0, f'dev startup must not auto-seed, got {n}'\n"
        "print('dev-sqlite-ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd=BACKEND_ROOT, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "dev-sqlite-ok" in result.stdout


# ── Test F — Phase 7 test isolation still functional ─────────────────────────
def test_f_test_isolation_still_functional():
    # Guard still rejects non-SQLite test targets.
    with pytest.raises(RuntimeError):
        assert_test_url_isolation(
            "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb",
            "postgresql+asyncpg://app:fake-secret@db.example:5432/flightdb",
        )

    # The production URL + isolated SQLite test URL remain a valid pair.
    assert assert_test_url_isolation(EFFECTIVE_DATABASE_URL, settings.DATABASE_URL) is None

    # TEST_DATABASE_URL never leaks into the production URL.
    assert EFFECTIVE_DATABASE_URL != settings.DATABASE_URL
    assert settings.TEST_DATABASE_URL.startswith("sqlite+aiosqlite:///")


# ── Test G — Alembic resolves the configured production URL, no secrets ──────
def test_g_alembic_resolves_production_url_without_exposing_secrets():
    fake_password = "sekrit-please-do-not-leak"
    env = os.environ.copy()
    env["ENVIRONMENT"] = "development"
    env["DATABASE_URL"] = (
        "postgresql://app:" + fake_password + "@db-host.example.invalid:5432/flightdb"
        "?sslmode=require&channel_binding=require"
    )

    # Offline mode ("--sql") resolves env.py's URL from settings and renders
    # DDL without ever connecting to a database — read-only and configuration-
    # focused, with a fake URL.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True, text=True, cwd=BACKEND_ROOT, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "CREATE TABLE" in combined
    assert fake_password not in combined, "Alembic output leaked a database credential"
    assert "db-host.example.invalid" not in combined