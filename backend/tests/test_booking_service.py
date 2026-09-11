"""
Phase 12 — Booking Service tests.

Comprehensive test suite for BookingService:
- Booking creation with validation
- State transitions
- Seat availability
- Price calculation
- Ownership checks
- Cancellation and seat restoration
"""
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal, init_db
from services.booking_service import BookingService
from services.flight_service import FlightService
from models.booking import Booking, BookingStatus, Passenger
from models.flight import Flight, CabinClass
from models.user import User
from agents import set_tracing_disabled

set_tracing_disabled(True)


async def setup_test_data(session: AsyncSession):
    """Create a test user, flight, and return their IDs."""
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        phone="1234567890",
    )
    session.add(user)

    # Create flight
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
    await session.flush()
    return user_id, flight_id


async def test_1_create_valid_booking():
    """Test: Create valid booking with all required fields."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
                "passport_number": "ABC123456",
                "nationality": "Pakistan",
            }
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            cabin_class="economy",
            contact_email="john@example.com",
            contact_phone="1234567890",
        )

        assert response.success is True, f"Expected success, got: {response.message}"
        assert response.pnr != "", "PNR should not be empty"
        assert response.booking_id != "", "booking_id should not be empty"
        assert response.total_amount > 0, "total_amount should be positive"
        print(f"[PASS] Test 1: Valid booking created (PNR: {response.pnr})")


async def test_2_flight_not_found():
    """Test: Booking fails when flight does not exist."""
    async with AsyncSessionLocal() as session:
        user_id, _ = await setup_test_data(session)
        fake_flight_id = str(uuid.uuid4())

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=fake_flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert response.success is False
        assert "not found" in response.message.lower()
        print("[PASS] Test 2: Flight not found correctly rejected")


async def test_3_insufficient_seats():
    """Test: Booking fails when insufficient seats available."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Set available seats to 0
        result = await session.execute(
            __import__("sqlalchemy").select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalars().first()
        flight.available_seats = 0
        await session.flush()

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert response.success is False
        assert "insufficient" in response.message.lower()
        print("[PASS] Test 3: Insufficient seats correctly rejected")


async def test_4_invalid_passenger_data():
    """Test: Booking fails with invalid passenger data."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Missing first_name
        passengers = [
            {
                "first_name": "",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert response.success is False
        assert "invalid" in response.message.lower()
        print("[PASS] Test 4: Invalid passenger data correctly rejected")


async def test_5_server_side_price_calculation():
    """Test: Price is calculated server-side, not trusted from client."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            },
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "date_of_birth": "1992-03-20",
            },
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert response.success is True
        # Flight base price: 150, tax: 15%, so per person = 150 * 1.15 = 172.5
        expected_per_person = 150 * 1.15
        expected_total = expected_per_person * 2
        assert response.total_amount == expected_total
        print(f"[PASS] Test 5: Price calculated correctly ({response.total_amount})")


async def test_6_unique_pnr_generation():
    """Test: Each booking gets a unique PNR."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        pnrs = set()
        for i in range(5):
            passengers = [
                {
                    "first_name": f"John{i}",
                    "last_name": "Doe",
                    "date_of_birth": "1990-05-15",
                }
            ]

            response = await BookingService.create_booking(
                session,
                user_id=user_id,
                flight_id=flight_id,
                passengers=passengers,
                contact_email=f"john{i}@example.com",
            )

            assert response.success is True
            assert response.pnr not in pnrs, "PNR should be unique"
            pnrs.add(response.pnr)

        assert len(pnrs) == 5
        print(f"[PASS] Test 6: All {len(pnrs)} PNRs are unique")


async def test_7_confirm_pending_booking():
    """Test: Confirm a pending booking."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert create_response.success is True
        booking_id = create_response.booking_id

        # Confirm the booking
        confirm_response = await BookingService.confirm_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        assert confirm_response.success is True
        assert confirm_response.status == "confirmed"
        print("[PASS] Test 7: Pending booking confirmed successfully")


async def test_8_invalid_confirmation():
    """Test: Cannot confirm non-pending booking."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        booking_id = create_response.booking_id

        # Confirm once
        await BookingService.confirm_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        # Try to confirm again
        confirm_response = await BookingService.confirm_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        assert confirm_response.success is False
        print("[PASS] Test 8: Cannot re-confirm confirmed booking")


async def test_9_retrieve_booking():
    """Test: Retrieve booking by PNR."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        pnr = create_response.pnr

        booking = await BookingService.get_booking(
            session,
            user_id=user_id,
            pnr=pnr,
        )

        assert booking is not None
        assert booking.pnr == pnr
        assert booking.user_id == user_id
        print(f"[PASS] Test 9: Booking retrieved (PNR: {pnr})")


async def test_10_list_user_bookings():
    """Test: List user's bookings with ownership check."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Create 3 bookings
        for i in range(3):
            passengers = [
                {
                    "first_name": f"John{i}",
                    "last_name": "Doe",
                    "date_of_birth": "1990-05-15",
                }
            ]

            await BookingService.create_booking(
                session,
                user_id=user_id,
                flight_id=flight_id,
                passengers=passengers,
                contact_email=f"john{i}@example.com",
            )

        bookings = await BookingService.list_user_bookings(
            session,
            user_id=user_id,
        )

        assert len(bookings) == 3
        print(f"[PASS] Test 10: Listed {len(bookings)} bookings for user")


async def test_11_user_isolation():
    """Test: User A cannot see User B's bookings."""
    async with AsyncSessionLocal() as session:
        # Create two users
        user_id_a = str(uuid.uuid4())
        user_a = User(
            id=user_id_a,
            email=f"user_a_{uuid.uuid4().hex[:8]}@example.com",
            name="User A",
        )
        session.add(user_a)

        user_id_b = str(uuid.uuid4())
        user_b = User(
            id=user_id_b,
            email=f"user_b_{uuid.uuid4().hex[:8]}@example.com",
            name="User B",
        )
        session.add(user_b)

        # Create flight
        flight_id = str(uuid.uuid4())
        flight = Flight(
            id=flight_id,
            flight_number="TEST-200",
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
        await session.flush()

        # User A books
        passengers = [
            {
                "first_name": "A",
                "last_name": "Person",
                "date_of_birth": "1990-05-15",
            }
        ]

        await BookingService.create_booking(
            session,
            user_id=user_id_a,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="a@example.com",
        )

        # User B tries to list User A's bookings
        bookings_b = await BookingService.list_user_bookings(
            session,
            user_id=user_id_b,
        )

        assert len(bookings_b) == 0
        print("[PASS] Test 11: User isolation enforced")


async def test_12_cancel_booking():
    """Test: Cancel a booking."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        booking_id = create_response.booking_id

        cancel_response = await BookingService.cancel_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
            reason="Changed my mind",
        )

        assert cancel_response.success is True
        assert cancel_response.status == "cancelled"
        print("[PASS] Test 12: Booking cancelled successfully")


async def test_13_cancelled_cannot_be_confirmed():
    """Test: Cannot confirm a cancelled booking."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            }
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        booking_id = create_response.booking_id

        # Cancel
        await BookingService.cancel_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        # Try to confirm
        confirm_response = await BookingService.confirm_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        assert confirm_response.success is False
        print("[PASS] Test 13: Cancelled booking cannot be confirmed")


async def test_14_cancellation_restores_seats():
    """Test: Cancellation restores seats to the flight."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Get initial seat count
        result = await session.execute(
            __import__("sqlalchemy").select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalars().first()
        initial_seats = flight.available_seats

        # Book 2 passengers
        passengers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
            },
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "date_of_birth": "1992-03-20",
            },
        ]

        create_response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        booking_id = create_response.booking_id

        # Check seats reduced
        result = await session.execute(
            __import__("sqlalchemy").select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalars().first()
        after_booking_seats = flight.available_seats
        assert after_booking_seats == initial_seats - 2

        # Cancel
        await BookingService.cancel_booking(
            session,
            user_id=user_id,
            booking_id=booking_id,
        )

        # Check seats restored
        result = await session.execute(
            __import__("sqlalchemy").select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalars().first()
        after_cancel_seats = flight.available_seats
        assert after_cancel_seats == initial_seats

        print("[PASS] Test 14: Cancellation restores seats")


async def test_15_transaction_rollback():
    """Test: Partial booking failure rolls back transaction."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Create 3 passengers, last one with invalid date
        passengers = [
            {"first_name": "John", "last_name": "Doe", "date_of_birth": "1990-05-15"},
            {"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1992-03-20"},
            {"first_name": "Bob", "last_name": "Smith", "date_of_birth": "invalid"},
        ]

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=passengers,
            contact_email="john@example.com",
        )

        assert response.success is False

        # Verify no booking was created
        bookings = await BookingService.list_user_bookings(
            session,
            user_id=user_id,
        )
        assert len(bookings) == 0

        # Verify seats were not reduced
        result = await session.execute(
            __import__("sqlalchemy").select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalars().first()
        assert flight.available_seats == 180

        print("[PASS] Test 15: Transaction rolled back on partial failure")


async def main():
    """Run all booking service tests."""
    await init_db()

    tests = [
        test_1_create_valid_booking,
        test_2_flight_not_found,
        test_3_insufficient_seats,
        test_4_invalid_passenger_data,
        test_5_server_side_price_calculation,
        test_6_unique_pnr_generation,
        test_7_confirm_pending_booking,
        test_8_invalid_confirmation,
        test_9_retrieve_booking,
        test_10_list_user_bookings,
        test_11_user_isolation,
        test_12_cancel_booking,
        test_13_cancelled_cannot_be_confirmed,
        test_14_cancellation_restores_seats,
        test_15_transaction_rollback,
    ]

    print("=" * 70)
    print("PHASE 12 — BOOKING SERVICE TESTS")
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
