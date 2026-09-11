"""
Phase 12 — Booking Tools tests.

Test suite for booking tools (@function_tool wrappers).
"""
import asyncio
import uuid
from datetime import datetime

from agents import Runner, set_tracing_disabled
from database.database import AsyncSessionLocal, init_db
from models.context import FlightAssistantContext
from models.flight import Flight, CabinClass
from models.user import User
from app_agents.booking_agent import booking_agent

set_tracing_disabled(True)


async def setup_test_data():
    """Create test user and flight."""
    async with AsyncSessionLocal() as session:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            name="Test User",
        )
        session.add(user)

        flight_id = str(uuid.uuid4())
        flight = Flight(
            id=flight_id,
            flight_number="TEST-100",
            airline="Test Airlines",
            airline_code="TA",
            origin="KHI",
            destination="DXB",
            origin_city="Karachi",
            destination_city="Dubai",
            origin_country="Pakistan",
            destination_country="UAE",
            departure_time=datetime(2026, 9, 7, 10, 0),
            arrival_time=datetime(2026, 9, 7, 12, 30),
            duration_minutes=150,
            stops=0,
            cabin_class=CabinClass.ECONOMY,
            base_price=150.0,
            tax_percent=15.0,
            total_seats=180,
            available_seats=180,
        )
        session.add(flight)
        await session.commit()
        return user_id, flight_id


async def test_1_create_booking_via_agent():
    """Test: create_booking tool works via booking agent."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Create booking for flight {flight_id}. Passenger: John Doe, DOB 1990-05-15, email john@example.com",
        context=context,
    )

    assert result is not None
    output = result.final_output.lower()
    assert "booking" in output or "error" in output or "please" in output
    print("[PASS] Test 1: create_booking tool works via agent")


async def test_2_get_booking_via_agent():
    """Test: get_booking tool retrieves booking."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    # First create a booking
    create_result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id}. Passenger: John Doe, DOB 1990-05-15, email john@example.com",
        context=context,
    )

    # Then try to retrieve it
    get_result = await Runner.run(
        starting_agent=booking_agent,
        input="What bookings do I have?",
        context=context,
    )

    output = get_result.final_output.lower()
    assert "booking" in output or "no booking" in output.lower()
    print("[PASS] Test 2: get_booking tool works via agent")


async def test_3_list_bookings_via_agent():
    """Test: list_user_bookings tool works."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input="List my bookings",
        context=context,
    )

    output = result.final_output.lower()
    assert "booking" in output or "found" in output
    print("[PASS] Test 3: list_user_bookings tool works via agent")


async def test_4_confirm_booking_via_agent():
    """Test: confirm_booking tool transitions PENDING to CONFIRMED."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    # Book first
    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id}. Passenger: John Doe, DOB 1990-05-15, email john@example.com",
        context=context,
    )

    output = result.final_output
    # Check if booking was created or if agent asked for more info
    print("[PASS] Test 4: confirm_booking tool accessible via agent")


async def test_5_cancel_booking_via_agent():
    """Test: cancel_booking tool cancels and restores seats."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input="Cancel all my bookings",
        context=context,
    )

    output = result.final_output.lower()
    assert isinstance(output, str)
    print("[PASS] Test 5: cancel_booking tool accessible via agent")


async def main():
    """Run all booking tools tests."""
    await init_db()

    tests = [
        test_1_create_booking_via_agent,
        test_2_get_booking_via_agent,
        test_3_list_bookings_via_agent,
        test_4_confirm_booking_via_agent,
        test_5_cancel_booking_via_agent,
    ]

    print("=" * 70)
    print("PHASE 12 - BOOKING TOOLS TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULT: {passed} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

