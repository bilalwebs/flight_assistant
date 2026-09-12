"""
Phase 7 — pytest configuration for the isolated test stack.

Decides ``TEST_DATABASE_URL`` (a fresh SQLite temp file) BEFORE any app/test
module imports ``database.database``, so the engine/session factory bind to the
isolated DB. Also wires the FastAPI ``get_db`` dependency override onto that
same session factory. A safety guard in ``database.database`` makes it
impossible for the test stack to target PostgreSQL/Neon or the dev database.
"""
import asyncio
import os
import uuid

import pytest

from tests.isolation import cleanup_temp_dir, make_test_url

# Must happen before any `from database.database import ...` runs (pytest loads
# this conftest ahead of test-module collection).
TEST_URL, TEST_ROOT = make_test_url()
os.environ["TEST_DATABASE_URL"] = TEST_URL


def pytest_sessionfinish(session, exitstatus):
    """Guaranteed temp-dir removal — even if collection aborted before fixtures."""
    cleanup_temp_dir(TEST_ROOT)


@pytest.fixture(scope="session", autouse=True)
def isolated_test_environment():
    """One reset+seed and one app override for the whole session; cleanup at end."""
    from database.database import (
        AsyncSessionLocal,
        engine,
        get_db,
        reset_test_db,
    )

    asyncio.run(reset_test_db())

    from main import app

    async def _override_get_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())
    cleanup_temp_dir(TEST_ROOT)


@pytest.fixture(scope="function")
def sync_flight_id():
    """Insert a bookable flight into the isolated test DB; return its ID.

    Lets the Phase 14 HTTP suite's ``test_*(sync_flight_id)`` functions run
    under pytest too (their standalone runner also passes an ID directly).
    """
    from datetime import datetime, timedelta, timezone

    from models.flight import CabinClass, Flight

    async def _create():
        from database.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            flight = Flight(
                id=str(uuid.uuid4()),
                flight_number=f"PF-{uuid.uuid4().hex[:4].upper()}",
                airline="Pytest Air",
                airline_code="PF",
                origin="KHI",
                destination="DXB",
                origin_city="Karachi",
                destination_city="Dubai",
                origin_country="Pakistan",
                destination_country="UAE",
                departure_time=datetime.now(timezone.utc) + timedelta(days=2),
                arrival_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
                duration_minutes=120,
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                base_price=150.0,
                tax_percent=15.0,
                total_seats=180,
                available_seats=180,
            )
            session.add(flight)
            await session.commit()
            return flight.id

    return asyncio.run(_create())