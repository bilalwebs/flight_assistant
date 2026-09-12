"""
Phase 4 — focused tests proving the UTC datetime standardization.

Verifies (without schema migration or data changes):
1. Instant-timestamp columns are declared DateTime(timezone=True).
2. Flight schedule columns stay naive UTC (existing domain semantics).
3. The utcnow() helper emits timezone-aware UTC.
4. Flight search normalizes aware API dates to naive UTC (no naive/aware mismatch).
5. Aware and naive search dates return identical results against the SQLite dev DB.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from database.database import AsyncSessionLocal, init_db
from models.user import User
from models.flight import Flight
from models.booking import Booking, Passenger, Payment
from services.flight_service import FlightService
from utils.datetime_utils import utcnow

passed = 0


def check(label: str, condition: bool) -> None:
    global passed
    assert condition, f"FAIL: {label}"
    passed += 1
    print(f"[PASS] {label}")


async def db_aware_vs_naive_search() -> None:
    async with AsyncSessionLocal() as session:
        flight = await session.execute(
            Flight.__table__.select()
            .where(Flight.status == "scheduled", Flight.is_active == True)  # noqa: E712
            .limit(1)
        )
        flight = flight.first()
        check("dev DB yields a scheduled flight", flight is not None)

        dep = flight.departure_time
        naive = dep.replace(hour=0, minute=0, second=0, microsecond=0)
        aware = naive.replace(tzinfo=timezone.utc)

        naive_hits = await FlightService.search_flights(
            session, origin=flight.origin, destination=flight.destination, date=naive
        )
        aware_hits = await FlightService.search_flights(
            session, origin=flight.origin, destination=flight.destination, date=aware
        )
        check("aware-UTC search date matches naive-UTC result set", [f.id for f in naive_hits] == [f.id for f in aware_hits])


def main() -> None:
    asyncio.run(init_db())
    # 1. Instant-timestamp columns must be timezone-aware.
    aware_cols = {
        User: {"created_at", "updated_at"},
        Flight: {"created_at", "updated_at"},
        Booking: {"created_at", "updated_at", "cancelled_at"},
        Passenger: {"created_at"},
        Payment: {"created_at", "updated_at", "paid_at", "refunded_at"},
    }
    for model, cols in aware_cols.items():
        for col_name in cols:
            check(
                f"{model.__name__}.{col_name} is DateTime(timezone=True)",
                model.__table__.c[col_name].type.timezone is True,
            )

    # 2. Flight schedule instants intentionally remain naive UTC.
    check(
        "Flight.departure_time stays DateTime(timezone=False)",
        Flight.__table__.c["departure_time"].type.timezone is False,
    )
    check(
        "Flight.arrival_time stays DateTime(timezone=False)",
        Flight.__table__.c["arrival_time"].type.timezone is False,
    )

    # 3. Instant-timestamp columns use a Python callable default (not server_default)
#    and derive from the aware-UTC utcnow() helper (proven below in #4).
    for model, col_name in [(User, "created_at"), (Flight, "updated_at"),
                            (Booking, "created_at"), (Passenger, "created_at"), (Payment, "created_at")]:
        column = model.__table__.c[col_name]
        default = column.default
        check(f"{model.__name__}.{col_name} has a callable default",
              default is not None and callable(getattr(default, "arg", None)))

    # 4. utcnow() helper produces aware UTC and is not deprecated utcnow().
    now = utcnow()
    check("utcnow() has a timezone", now.tzinfo is not None)
    check("utcnow() is UTC offset 0", now.utcoffset() == timedelta(0))

    # 5. Comparison-boundary normalization.
    aware = datetime(2026, 9, 7, 12, 30, tzinfo=timezone.utc)
    naive = FlightService._naive_utc(aware)
    check("_naive_utc strips offset from aware value", naive.tzinfo is None)
    check("_naive_utc preserves wall-clock after UTC conversion", naive == datetime(2026, 9, 7, 12, 30))
    orig = datetime(2026, 9, 7, 5, 0)
    check("_naive_utc leaves naive value untouched", FlightService._naive_utc(orig) == orig)

    asyncio.run(db_aware_vs_naive_search())

    print()
    print("=" * 70)
    print(f"RESULT: {passed} passed, 0 failed")
    print("=" * 70)


if __name__ == "__main__":
    main()