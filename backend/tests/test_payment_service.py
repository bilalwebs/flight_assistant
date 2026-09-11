"""
Phase 13 — Payment Service Tests.

Test suite for PaymentService: payment creation, webhook verification, idempotency.
Uses unittest.mock to mock Stripe API calls without making real requests.
"""
import asyncio
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal, init_db
from services.payment_service import PaymentService
from models.booking import Booking, BookingStatus, Payment, PaymentStatus, PaymentMethod
from models.flight import Flight, CabinClass
from models.user import User
from agents import set_tracing_disabled

set_tracing_disabled(True)


async def setup_test_data(session: AsyncSession):
    """Create test user, flight, and pending booking."""
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
        flight_number="PAYMENT-100",
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

    # Create booking
    booking_id = str(uuid.uuid4())
    booking = Booking(
        id=booking_id,
        pnr="TEST001",
        user_id=user_id,
        flight_id=flight_id,
        cabin_class="economy",
        status=BookingStatus.PENDING,
        passenger_count=1,
        base_amount=150.0,
        tax_amount=22.5,
        total_amount=172.5,
        currency="USD",
        contact_email="test@example.com",
    )
    session.add(booking)
    await session.flush()

    return user_id, flight_id, booking_id


@patch("services.payment_service.stripe.checkout.Session.create")
async def test_1_create_payment(mock_create):
    """Test: Create payment for valid pending booking."""
    # Mock Stripe response
    mock_create.return_value = MagicMock(
        id="cs_test_123",
        url="https://checkout.stripe.com/pay/cs_test_123"
    )

    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        response = await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )

        assert response["success"] is True, f"Expected success, got: {response['message']}"
        assert response["session_id"] is not None
        assert response["checkout_url"] is not None
        print("[PASS] Test 1: Payment created successfully")


async def test_2_booking_not_found():
    """Test: Payment creation fails for non-existent booking."""
    async with AsyncSessionLocal() as session:
        user_id = str(uuid.uuid4())
        fake_booking_id = str(uuid.uuid4())

        response = await PaymentService.create_payment(
            session,
            booking_id=fake_booking_id,
            user_id=user_id,
        )

        assert response["success"] is False
        assert "not found" in response["message"].lower()
        print("[PASS] Test 2: Non-existent booking rejected")


async def test_3_unauthorized_user():
    """Test: User cannot create payment for another user's booking."""
    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)
        other_user_id = str(uuid.uuid4())

        response = await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=other_user_id,
        )

        assert response["success"] is False
        assert "own" in response["message"].lower() or "not" in response["message"].lower()
        print("[PASS] Test 3: Unauthorized user rejected")


async def test_4_confirmed_booking_not_payable():
    """Test: Cannot create payment for already-confirmed booking."""
    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Mark booking as confirmed
        result = await session.execute(
            __import__("sqlalchemy").select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalars().first()
        booking.status = BookingStatus.CONFIRMED
        await session.flush()

        response = await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )

        assert response["success"] is False
        assert "confirmed" in response["message"].lower() or "cannot" in response["message"].lower()
        print("[PASS] Test 4: Confirmed booking not payable")


@patch("services.payment_service.stripe.checkout.Session.create")
async def test_5_duplicate_active_payment(mock_create):
    """Test: Creating second payment for same booking returns existing session (idempotent)."""
    mock_create.return_value = MagicMock(
        id="cs_test_dup",
        url="https://checkout.stripe.com/pay/cs_test_dup"
    )

    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Create first payment
        response1 = await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )
        assert response1["success"] is True
        first_session_id = response1["session_id"]

        # Try to create second payment
        response2 = await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )

        assert response2["success"] is True
        assert response2["session_id"] == first_session_id
        print("[PASS] Test 5: Duplicate payment returns existing session (idempotent)")


@patch("services.payment_service.stripe.checkout.Session.create")
async def test_6_get_payment_status(mock_create):
    """Test: Retrieve payment status."""
    mock_create.return_value = MagicMock(
        id="cs_test_status",
        url="https://checkout.stripe.com/pay/cs_test_status"
    )

    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Create payment
        await PaymentService.create_payment(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )

        # Get status
        response = await PaymentService.get_payment_status(
            session,
            booking_id=booking_id,
            user_id=user_id,
        )

        assert response["success"] is True
        assert response["payment"]["status"] == "pending"
        print("[PASS] Test 6: Payment status retrieved")


async def test_7_webhook_charge_succeeded():
    """Test: Webhook charge.succeeded event confirms booking."""
    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Create payment directly
        payment_id = str(uuid.uuid4())
        payment = Payment(
            id=payment_id,
            booking_id=booking_id,
            amount=172.5,
            currency="USD",
            method=PaymentMethod.STRIPE,
            status=PaymentStatus.PENDING,
            stripe_checkout_session_id="cs_test_webhook",
        )
        session.add(payment)
        await session.flush()

        # Simulate webhook event
        event = {
            "id": "evt_test_123",
            "type": "charge.succeeded",
            "data": {
                "object": {
                    "id": "ch_test_123",
                    "payment_intent": "pi_test_123",
                    "amount": 17250,
                    "currency": "usd",
                    "metadata": {
                        "booking_id": booking_id,
                        "user_id": user_id,
                    },
                }
            },
        }

        result = await PaymentService.verify_payment_from_webhook(session, event)

        assert result["success"] is True
        assert result["booking_confirmed"] is True
        print("[PASS] Test 7: Webhook charge.succeeded confirms booking")


async def test_8_webhook_charge_failed():
    """Test: Webhook charge.failed event marks payment as failed."""
    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Create payment
        payment_id = str(uuid.uuid4())
        payment = Payment(
            id=payment_id,
            booking_id=booking_id,
            amount=172.5,
            currency="USD",
            method=PaymentMethod.STRIPE,
            status=PaymentStatus.PENDING,
        )
        session.add(payment)
        await session.flush()

        # Simulate failed charge event
        event = {
            "id": "evt_test_failed",
            "type": "charge.failed",
            "data": {
                "object": {
                    "id": "ch_test_failed",
                    "metadata": {
                        "booking_id": booking_id,
                        "user_id": user_id,
                    },
                }
            },
        }

        result = await PaymentService.verify_payment_from_webhook(session, event)

        assert result["success"] is False
        assert "failed" in result["message"].lower()
        print("[PASS] Test 8: Webhook charge.failed marks payment as failed")


async def test_9_webhook_idempotency():
    """Test: Same webhook event processed only once (idempotent)."""
    async with AsyncSessionLocal() as session:
        user_id, _, booking_id = await setup_test_data(session)

        # Create payment
        payment_id = str(uuid.uuid4())
        payment = Payment(
            id=payment_id,
            booking_id=booking_id,
            amount=172.5,
            currency="USD",
            method=PaymentMethod.STRIPE,
            status=PaymentStatus.PENDING,
        )
        session.add(payment)
        await session.flush()

        event = {
            "id": "evt_test_idempotent",
            "type": "charge.succeeded",
            "data": {
                "object": {
                    "id": "ch_test_idempotent",
                    "payment_intent": "pi_test_idempotent",
                    "amount": 17250,
                    "currency": "usd",
                    "metadata": {
                        "booking_id": booking_id,
                        "user_id": user_id,
                    },
                }
            },
        }

        # Process same event twice
        result1 = await PaymentService.verify_payment_from_webhook(session, event)
        result2 = await PaymentService.verify_payment_from_webhook(session, event)

        assert result1["success"] is True
        assert result2["success"] is True
        assert result2.get("already_processed") is True
        print("[PASS] Test 9: Webhook idempotency enforced")


async def run_tests():
    """Run all payment service tests."""
    await init_db()

    tests = [
        ("test_1_create_payment", test_1_create_payment()),
        ("test_2_booking_not_found", test_2_booking_not_found()),
        ("test_3_unauthorized_user", test_3_unauthorized_user()),
        ("test_4_confirmed_booking_not_payable", test_4_confirmed_booking_not_payable()),
        ("test_5_duplicate_active_payment", test_5_duplicate_active_payment()),
        ("test_6_get_payment_status", test_6_get_payment_status()),
        ("test_7_webhook_charge_succeeded", test_7_webhook_charge_succeeded()),
        ("test_8_webhook_charge_failed", test_8_webhook_charge_failed()),
        ("test_9_webhook_idempotency", test_9_webhook_idempotency()),
    ]

    print("=" * 70)
    print("PHASE 13 - PAYMENT SERVICE TESTS")
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
