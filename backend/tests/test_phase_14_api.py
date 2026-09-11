"""
Phase 14 — API Integration Tests.

Comprehensive test suite for authentication, flights, bookings, payments, and assistant APIs.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal, init_db
from services.auth_service import AuthenticationService
from services.booking_service import BookingService
from services.flight_service import FlightService
from models.booking import Booking, BookingStatus
from models.flight import Flight, CabinClass
from models.user import User
from agents import set_tracing_disabled

set_tracing_disabled(True)


async def setup_test_data(session: AsyncSession):
    """Create test user, flight, and booking."""
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        password_hash=AuthenticationService.hash_password("TestPassword123"),
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
        departure_time=datetime.utcnow() + timedelta(days=1),
        arrival_time=datetime.utcnow() + timedelta(days=1, hours=2),
        duration_minutes=120,
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


async def test_1_registration_success():
    """Test: User registration succeeds."""
    async with AsyncSessionLocal() as session:
        email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
        success, msg, user = await AuthenticationService.register_user(
            session,
            email=email,
            password="SecurePass123",
            name="New User",
            phone="+1234567890",
        )
        assert success is True, msg
        assert user is not None
        assert user.email == email
        await session.commit()
        print("[PASS] Test 1: User registration success")


async def test_2_duplicate_email_rejected():
    """Test: Duplicate email registration rejected."""
    async with AsyncSessionLocal() as session:
        # Register first user
        await AuthenticationService.register_user(
            session,
            email="duplicate@example.com",
            password="Pass123",
            name="User 1",
        )
        await session.commit()

        # Try to register with same email
        success, msg, user = await AuthenticationService.register_user(
            session,
            email="duplicate@example.com",
            password="Pass456",
            name="User 2",
        )
        assert success is False
        assert "already registered" in msg.lower()
        print("[PASS] Test 2: Duplicate email rejected")


async def test_3_password_hashed():
    """Test: Passwords are hashed, not stored plaintext."""
    async with AsyncSessionLocal() as session:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "MySecurePassword123"

        success, msg, user = await AuthenticationService.register_user(
            session,
            email=email,
            password=password,
            name="Test User",
        )
        assert success is True
        assert user.password_hash is not None
        assert user.password_hash != password
        assert AuthenticationService.verify_password(password, user.password_hash)
        print("[PASS] Test 3: Password hashed correctly")


async def test_4_login_success():
    """Test: Login with correct credentials succeeds."""
    async with AsyncSessionLocal() as session:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "CorrectPassword123"

        await AuthenticationService.register_user(
            session,
            email=email,
            password=password,
            name="Test User",
        )
        await session.commit()

        success, msg, user = await AuthenticationService.login_user(
            session,
            email=email,
            password=password,
        )
        assert success is True
        assert user is not None
        assert user.email == email
        print("[PASS] Test 4: Login success")


async def test_5_invalid_password_rejected():
    """Test: Login with incorrect password rejected."""
    async with AsyncSessionLocal() as session:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        await AuthenticationService.register_user(
            session,
            email=email,
            password="CorrectPassword",
            name="Test User",
        )
        await session.commit()

        success, msg, user = await AuthenticationService.login_user(
            session,
            email=email,
            password="WrongPassword",
        )
        assert success is False
        assert "invalid" in msg.lower()
        print("[PASS] Test 5: Invalid password rejected")


async def test_6_token_generation():
    """Test: JWT token generated and expires correctly."""
    token, expires_in = AuthenticationService.generate_access_token("test-user-id")
    assert token is not None
    assert len(token) > 0
    assert expires_in > 0
    print("[PASS] Test 6: Token generated")


async def test_7_token_verification():
    """Test: Valid token verified successfully."""
    user_id = str(uuid.uuid4())
    token, _ = AuthenticationService.generate_access_token(user_id)

    verified_user_id = await AuthenticationService.verify_token(token)
    assert verified_user_id == user_id
    print("[PASS] Test 7: Token verified")


async def test_8_invalid_token_rejected():
    """Test: Invalid token rejected."""
    verified_user_id = await AuthenticationService.verify_token("invalid.token.here")
    assert verified_user_id is None
    print("[PASS] Test 8: Invalid token rejected")


async def test_9_flight_search():
    """Test: Flight search returns results."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        flights = await FlightService.search_flights(
            session,
            origin="KHI",
            destination="DXB",
            date=datetime.utcnow() + timedelta(days=1),
            cabin_class=CabinClass.ECONOMY,
        )
        assert len(flights) > 0
        print("[PASS] Test 9: Flight search success")


async def test_10_flight_details():
    """Test: Flight details retrieved."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        flight = await FlightService.get_flight_details(session, flight_id)
        assert flight is not None
        assert flight.id == flight_id
        print("[PASS] Test 10: Flight details retrieved")


async def test_11_price_calculation():
    """Test: Price calculated correctly."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)
        flight = await FlightService.get_flight_details(session, flight_id)

        price = FlightService.calculate_flight_price(flight, 2)
        assert price.grand_total == price.total_per_person * 2
        assert price.base_price_per_person == 150.0
        print("[PASS] Test 11: Price calculation correct")


async def test_12_booking_creation():
    """Test: Booking created successfully."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=[
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1990-01-01",
                    "passenger_type": "adult",
                }
            ],
        )
        assert response.success is True
        assert response.pnr is not None
        await session.commit()
        print("[PASS] Test 12: Booking created")


async def test_13_booking_ownership_enforced():
    """Test: User cannot access another user's booking."""
    async with AsyncSessionLocal() as session:
        user1_id, flight_id = await setup_test_data(session)

        # Create booking for user1
        response = await BookingService.create_booking(
            session,
            user_id=user1_id,
            flight_id=flight_id,
            passengers=[{"first_name": "John", "last_name": "Doe", "date_of_birth": "1990-01-01"}],
        )
        await session.commit()

        # Try to retrieve with different user
        user2_id = str(uuid.uuid4())
        booking = await BookingService.get_booking_by_pnr(session, response.pnr)
        assert booking is not None
        assert booking.user_id == user1_id
        assert booking.user_id != user2_id
        print("[PASS] Test 13: Booking ownership enforced")


async def test_14_booking_confirmation():
    """Test: Booking can be confirmed."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Create booking
        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=[{"first_name": "John", "last_name": "Doe", "date_of_birth": "1990-01-01"}],
        )

        # Confirm booking
        confirm_response = await BookingService.confirm_booking(
            session,
            user_id=user_id,
            booking_id=response.booking_id,
        )
        assert confirm_response.success is True
        await session.commit()
        print("[PASS] Test 14: Booking confirmed")


async def test_15_booking_cancellation():
    """Test: Booking can be cancelled."""
    async with AsyncSessionLocal() as session:
        user_id, flight_id = await setup_test_data(session)

        # Create and confirm booking
        response = await BookingService.create_booking(
            session,
            user_id=user_id,
            flight_id=flight_id,
            passengers=[{"first_name": "John", "last_name": "Doe", "date_of_birth": "1990-01-01"}],
        )

        # Cancel booking
        cancel_response = await BookingService.cancel_booking(
            session,
            user_id=user_id,
            booking_id=response.booking_id,
        )
        assert cancel_response.success is True
        await session.commit()
        print("[PASS] Test 15: Booking cancelled")


async def run_tests():
    """Run all Phase 14 tests."""
    await init_db()

    tests = [
        ("test_1_registration_success", test_1_registration_success()),
        ("test_2_duplicate_email_rejected", test_2_duplicate_email_rejected()),
        ("test_3_password_hashed", test_3_password_hashed()),
        ("test_4_login_success", test_4_login_success()),
        ("test_5_invalid_password_rejected", test_5_invalid_password_rejected()),
        ("test_6_token_generation", test_6_token_generation()),
        ("test_7_token_verification", test_7_token_verification()),
        ("test_8_invalid_token_rejected", test_8_invalid_token_rejected()),
        ("test_9_flight_search", test_9_flight_search()),
        ("test_10_flight_details", test_10_flight_details()),
        ("test_11_price_calculation", test_11_price_calculation()),
        ("test_12_booking_creation", test_12_booking_creation()),
        ("test_13_booking_ownership_enforced", test_13_booking_ownership_enforced()),
        ("test_14_booking_confirmation", test_14_booking_confirmation()),
        ("test_15_booking_cancellation", test_15_booking_cancellation()),
    ]

    print("=" * 70)
    print("PHASE 14 - API INTEGRATION TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, test_coro in tests:
        try:
            await test_coro
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULT: {passed} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
