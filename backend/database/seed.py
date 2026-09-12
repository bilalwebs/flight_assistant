"""
Mock flight data seed.
Covers realistic Pakistan-origin international routes and a couple domestic.
Replace this module with a real flight-API integration in production.
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.flight import Flight, CabinClass, FlightStatus
from models.user import User, MembershipTier


# ──────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────

def _fid() -> str:
    return str(uuid.uuid4())


def _dt(base_date: datetime, hour: int, minute: int = 0) -> datetime:
    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _make_flight(
    flight_number: str,
    airline: str,
    airline_code: str,
    origin: str,
    destination: str,
    origin_city: str,
    destination_city: str,
    origin_country: str,
    destination_country: str,
    departure: datetime,
    duration_minutes: int,
    stops: int,
    cabin_class: CabinClass,
    base_price: float,
    available_seats: int,
    total_seats: int = 180,
    aircraft_type: str = "Boeing 737",
    carry_on_kg: int = 7,
    checked_baggage_kg: int = 23,
    stop_airports: list[str] | None = None,
    tax_percent: float = 15.0,
) -> dict[str, Any]:
    return {
        "id": _fid(),
        "flight_number": flight_number,
        "airline": airline,
        "airline_code": airline_code,
        "origin": origin,
        "destination": destination,
        "origin_city": origin_city,
        "destination_city": destination_city,
        "origin_country": origin_country,
        "destination_country": destination_country,
        "departure_time": departure,
        "arrival_time": departure + timedelta(minutes=duration_minutes),
        "duration_minutes": duration_minutes,
        "stops": stops,
        "stop_airports": json.dumps(stop_airports) if stop_airports else None,
        "cabin_class": cabin_class,
        "base_price": base_price,
        "tax_percent": tax_percent,
        "carry_on_kg": carry_on_kg,
        "checked_baggage_kg": checked_baggage_kg,
        "total_seats": total_seats,
        "available_seats": available_seats,
        "aircraft_type": aircraft_type,
        "status": FlightStatus.SCHEDULED,
        "is_active": True,
    }


# ──────────────────────────────────────────────────────────────
# Seed data builder
# ──────────────────────────────────────────────────────────────

def _build_flights() -> list[dict[str, Any]]:
    """Generate 30+ realistic flights across multiple routes and dates."""
    # Schedule instants are persisted as naive UTC (columns are DateTime
    # without timezone) — derive from aware UTC then strip the offset.
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    flights = []

    # Helper to add flights for multiple departure days
    def add(base: dict, day_offsets: list[int], hour_variants: list[int]) -> None:
        for day in day_offsets:
            dep_date = today + timedelta(days=day)
            for hour in hour_variants:
                entry = dict(base)
                entry["id"] = _fid()
                entry["departure_time"] = _dt(dep_date, hour)
                entry["arrival_time"] = entry["departure_time"] + timedelta(minutes=entry["duration_minutes"])
                flights.append(entry)

    # ── Karachi (KHI) → Dubai (DXB) ──────────────────────────
    khi_dxb_pk = _make_flight(
        flight_number="PK-201",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="KHI", destination="DXB",
        origin_city="Karachi", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 8), duration_minutes=120,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=210.0, available_seats=42, total_seats=180,
        aircraft_type="Airbus A320", carry_on_kg=7, checked_baggage_kg=23,
    )
    add(khi_dxb_pk, day_offsets=[1, 2, 3, 5, 7, 10], hour_variants=[8, 15, 22])

    khi_dxb_ek = _make_flight(
        flight_number="EK-601",
        airline="Emirates",
        airline_code="EK",
        origin="KHI", destination="DXB",
        origin_city="Karachi", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 10), duration_minutes=110,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=280.0, available_seats=65, total_seats=300,
        aircraft_type="Boeing 777", carry_on_kg=7, checked_baggage_kg=30,
    )
    add(khi_dxb_ek, day_offsets=[1, 2, 3, 5, 7, 10], hour_variants=[10, 17])

    khi_dxb_ek_biz = _make_flight(
        flight_number="EK-603",
        airline="Emirates",
        airline_code="EK",
        origin="KHI", destination="DXB",
        origin_city="Karachi", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 14), duration_minutes=110,
        stops=0, cabin_class=CabinClass.BUSINESS,
        base_price=950.0, available_seats=12, total_seats=42,
        aircraft_type="Boeing 777", carry_on_kg=12, checked_baggage_kg=40,
    )
    add(khi_dxb_ek_biz, day_offsets=[1, 3, 7, 10], hour_variants=[14])

    # ── Karachi (KHI) → Istanbul (IST) ───────────────────────
    khi_ist_pk = _make_flight(
        flight_number="PK-785",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="KHI", destination="IST",
        origin_city="Karachi", destination_city="Istanbul",
        origin_country="Pakistan", destination_country="Turkey",
        departure=_dt(today, 2), duration_minutes=390,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=520.0, available_seats=88, total_seats=200,
        aircraft_type="Boeing 777",
    )
    add(khi_ist_pk, day_offsets=[1, 3, 5, 8, 12], hour_variants=[2, 23])

    khi_ist_tk = _make_flight(
        flight_number="TK-708",
        airline="Turkish Airlines",
        airline_code="TK",
        origin="KHI", destination="IST",
        origin_city="Karachi", destination_city="Istanbul",
        origin_country="Pakistan", destination_country="Turkey",
        departure=_dt(today, 1), duration_minutes=360,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=610.0, available_seats=55, total_seats=250,
        aircraft_type="Boeing 787", carry_on_kg=8, checked_baggage_kg=30,
    )
    add(khi_ist_tk, day_offsets=[1, 4, 7, 11], hour_variants=[1, 20])

    # ── Lahore (LHE) → Dubai (DXB) ───────────────────────────
    lhe_dxb_pk = _make_flight(
        flight_number="PK-211",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="LHE", destination="DXB",
        origin_city="Lahore", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 9), duration_minutes=180,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=240.0, available_seats=70, total_seats=180,
        aircraft_type="Airbus A320",
    )
    add(lhe_dxb_pk, day_offsets=[1, 2, 4, 6, 9], hour_variants=[9, 18])

    lhe_dxb_fy = _make_flight(
        flight_number="FZ-351",
        airline="flydubai",
        airline_code="FZ",
        origin="LHE", destination="DXB",
        origin_city="Lahore", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 7), duration_minutes=185,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=190.0, available_seats=110, total_seats=180,
        aircraft_type="Boeing 737 MAX",
    )
    add(lhe_dxb_fy, day_offsets=[1, 3, 5, 8], hour_variants=[7, 21])

    # ── Islamabad (ISB) → Doha (DOH) ─────────────────────────
    isb_doh_pk = _make_flight(
        flight_number="PK-304",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="ISB", destination="DOH",
        origin_city="Islamabad", destination_city="Doha",
        origin_country="Pakistan", destination_country="Qatar",
        departure=_dt(today, 3), duration_minutes=210,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=310.0, available_seats=48, total_seats=180,
        aircraft_type="Airbus A330",
    )
    add(isb_doh_pk, day_offsets=[1, 3, 6, 9], hour_variants=[3, 16])

    isb_doh_qa = _make_flight(
        flight_number="QR-623",
        airline="Qatar Airways",
        airline_code="QR",
        origin="ISB", destination="DOH",
        origin_city="Islamabad", destination_city="Doha",
        origin_country="Pakistan", destination_country="Qatar",
        departure=_dt(today, 11), duration_minutes=195,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=380.0, available_seats=33, total_seats=250,
        aircraft_type="Airbus A350",
        carry_on_kg=7, checked_baggage_kg=30,
    )
    add(isb_doh_qa, day_offsets=[1, 4, 7, 10], hour_variants=[11, 23])

    # ── Karachi (KHI) → London (LHR) — 1-stop ────────────────
    khi_lhr_pk = _make_flight(
        flight_number="PK-757",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="KHI", destination="LHR",
        origin_city="Karachi", destination_city="London",
        origin_country="Pakistan", destination_country="UK",
        departure=_dt(today, 23), duration_minutes=510,
        stops=1, cabin_class=CabinClass.ECONOMY,
        base_price=720.0, available_seats=25, total_seats=200,
        aircraft_type="Boeing 777",
        stop_airports=["IST"],
    )
    add(khi_lhr_pk, day_offsets=[2, 5, 9, 14], hour_variants=[23])

    # ── Karachi (KHI) → Riyadh (RUH) ─────────────────────────
    khi_ruh_sv = _make_flight(
        flight_number="SV-792",
        airline="Saudia",
        airline_code="SV",
        origin="KHI", destination="RUH",
        origin_city="Karachi", destination_city="Riyadh",
        origin_country="Pakistan", destination_country="Saudi Arabia",
        departure=_dt(today, 6), duration_minutes=165,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=290.0, available_seats=60, total_seats=200,
        aircraft_type="Airbus A320",
    )
    add(khi_ruh_sv, day_offsets=[1, 3, 5, 7, 10], hour_variants=[6, 19])

    # ── Islamabad (ISB) → Dubai (DXB) ────────────────────────
    isb_dxb_g9 = _make_flight(
        flight_number="G9-411",
        airline="Air Arabia",
        airline_code="G9",
        origin="ISB", destination="DXB",
        origin_city="Islamabad", destination_city="Dubai",
        origin_country="Pakistan", destination_country="UAE",
        departure=_dt(today, 5), duration_minutes=195,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=175.0, available_seats=130, total_seats=180,
        aircraft_type="Airbus A320",
    )
    add(isb_dxb_g9, day_offsets=[1, 2, 4, 6, 8, 11], hour_variants=[5, 14, 21])

    # ── Domestic: Karachi (KHI) → Lahore (LHE) ───────────────
    khi_lhe_pk = _make_flight(
        flight_number="PK-100",
        airline="Pakistan International Airlines",
        airline_code="PK",
        origin="KHI", destination="LHE",
        origin_city="Karachi", destination_city="Lahore",
        origin_country="Pakistan", destination_country="Pakistan",
        departure=_dt(today, 7), duration_minutes=75,
        stops=0, cabin_class=CabinClass.ECONOMY,
        base_price=65.0, available_seats=90, total_seats=180,
        aircraft_type="ATR 72",
    )
    add(khi_lhe_pk, day_offsets=[1, 2, 3, 4, 5, 6, 7], hour_variants=[7, 10, 13, 16, 19])

    return flights


# ──────────────────────────────────────────────────────────────
# Demo users
# ──────────────────────────────────────────────────────────────

def _build_users() -> list[dict[str, Any]]:
    return [
        {
            "id": _fid(),
            "email": "bilal@example.com",
            "name": "Bilal Hussain",
            "phone": "+92-300-1234567",
            "membership": MembershipTier.PLATINUM,
            "loyalty_points": "15000",
        },
        {
            "id": _fid(),
            "email": "sara@example.com",
            "name": "Sara Khan",
            "phone": "+92-321-9876543",
            "membership": MembershipTier.GOLD,
            "loyalty_points": "4200",
        },
        {
            "id": _fid(),
            "email": "guest@example.com",
            "name": "Guest User",
            "phone": None,
            "membership": MembershipTier.STANDARD,
            "loyalty_points": "0",
        },
    ]


# ──────────────────────────────────────────────────────────────
# Main seed function
# ──────────────────────────────────────────────────────────────

async def seed_database(session: AsyncSession) -> dict[str, int]:
    """
    Insert seed data idempotently.

    - Flights are inserted only when the ``flights`` table is empty, which is
      the canonical signal that the schema was never initialized. Re-running
      the seed on an already populated database never adds or rewrites flights.
    - Demo users are keyed by their unique email: each is inserted only when
      the email is not already present. Running the seed twice (or on a
      database that has flights but is missing a demo user) inserts only the
      missing demo users — never duplicates.

    No bookings, passengers or payments are ever created. Returns counts of
    newly inserted records.
    """
    counts = {"flights": 0, "users": 0}

    # Flights: canonical initial load for an empty schema. Once any flight
    # exists, flight seeding is skipped so repeat runs cannot duplicate rows.
    existing = await session.execute(select(Flight).limit(1))
    if not existing.scalars().first():
        flight_dicts = _build_flights()
        for fdata in flight_dicts:
            session.add(Flight(**fdata))
        counts["flights"] = len(flight_dicts)

    # Users: demo accounts are additive and email-keyed. Each user is inserted
    # only if its canonical email does not already exist, so these passes are
    # repeat-safe and restore missing demo users without touching existing ones.
    user_dicts = _build_users()
    existing_emails = set((await session.execute(select(User.email))).scalars())
    for udata in user_dicts:
        if udata["email"] not in existing_emails:
            session.add(User(**udata))
            counts["users"] += 1

    await session.commit()
    return counts
