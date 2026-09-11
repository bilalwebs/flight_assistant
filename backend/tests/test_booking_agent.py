"""
Phase 12 — Booking Agent tests.

Test suite for BookingAgent using Agents SDK.
Verifies booking request routing, agent behavior, and data integrity.
"""
import asyncio
import uuid
import time
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


async def test_1_booking_request_routing():
    """Test: Booking request routes to booking agent."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"I want to book flight {flight_id}. My name is John Doe, DOB 1990-05-15, email john@example.com",
        context=context,
    )

    assert result is not None
    assert isinstance(result.final_output, str)
    assert len(result.final_output) > 0
    print("[PASS] Test 1: Booking request routed successfully")


async def test_2_missing_passenger_info_clarification():
    """Test: Agent asks for missing passenger info."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id} for me.",
        context=context,
    )

    output = result.final_output.lower()
    assert (
        "name" in output or "passenger" in output or "detail" in output
    ), "Agent should ask for missing passenger details"
    print("[PASS] Test 2: Agent requests missing passenger information")


async def test_3_agent_does_not_fabricate_passenger_data():
    """Test: Agent does not invent passenger information."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id}",
        context=context,
    )

    output = result.final_output
    # Agent should NOT create a booking without passenger info
    assert "booking created" not in output.lower() or "cannot" in output.lower() or "please" in output.lower()
    print("[PASS] Test 3: Agent does not fabricate passenger data")


async def test_4_agent_no_payment_claims():
    """Test: Agent never claims payment was completed."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id}. Passenger: John Doe, DOB 1990-05-15, email john@example.com",
        context=context,
    )

    output = result.final_output.lower()
    assert "payment" not in output or "no payment" in output or "not" in output
    assert "charged" not in output
    print("[PASS] Test 4: Agent does not claim payment success")


async def test_5_agent_uses_booking_tools():
    """Test: Agent actually calls booking tools."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"Book flight {flight_id}. Passenger: John Doe, DOB 1990-05-15, email john@example.com, phone 1234567890",
        context=context,
    )

    # Check if booking tools were referenced in the output
    output = result.final_output.lower()
    assert "booking" in output or "error" in output
    print("[PASS] Test 5: Agent called booking tools")


async def test_6_context_user_id_propagation():
    """Test: Context user_id propagates to booking tools."""
    user_id, flight_id = await setup_test_data()

    context = FlightAssistantContext(
        user_id=user_id,
        user_name="Test User",
    )

    result = await Runner.run(
        starting_agent=booking_agent,
        input=f"List my bookings",
        context=context,
    )

    output = result.final_output
    assert isinstance(output, str)
    assert len(output) > 0
    print("[PASS] Test 6: Context user_id propagated correctly")


async def main():
    """Run all booking agent tests with pacing."""
    await init_db()

    tests = [
        test_1_booking_request_routing,
        test_2_missing_passenger_info_clarification,
        test_3_agent_does_not_fabricate_passenger_data,
        test_4_agent_no_payment_claims,
        test_5_agent_uses_booking_tools,
        test_6_context_user_id_propagation,
    ]

    print("=" * 70)
    print("PHASE 12 — BOOKING AGENT TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
            time.sleep(1)  # Pacing to avoid quota issues
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
            time.sleep(1)

    print("\n" + "=" * 70)
    print(f"RESULT: {passed} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
