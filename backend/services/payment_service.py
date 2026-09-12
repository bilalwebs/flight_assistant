"""
Phase 13 — Payment Service with Stripe Integration.

Business logic for payment operations: creation, verification, and booking confirmation.
Handles Stripe checkout sessions, webhook verification, and idempotency.
"""
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from config.settings import STRIPE_SECRET_KEY
from models.booking import Booking, BookingStatus, Payment, PaymentStatus, PaymentMethod
from utils.datetime_utils import utcnow
from models.responses import BookingResponse
from services.booking_service import BookingService

# Configure Stripe ONLY when credentials are present.
# Stripe is an OPTIONAL/future payment module — the application must start and
# operate fully without it. Initializing the SDK with an empty key is avoided.
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


class PaymentService:
    """Business logic for payment operations with Stripe.

    Stripe is an optional payment module. When STRIPE_SECRET_KEY is not
    configured, payment creation returns a clear configuration error and the
    booking flow proceeds via direct confirmation (PENDING -> CONFIRMED).
    """

    @staticmethod
    def is_configured() -> bool:
        """Return True when Stripe is configured (optional future module)."""
        return bool(STRIPE_SECRET_KEY)

    @staticmethod
    async def create_payment(
        session: AsyncSession,
        booking_id: str,
        user_id: str,
        success_url: str = "http://localhost:3000/payment/success",
        cancel_url: str = "http://localhost:3000/payment/cancel",
    ) -> dict:
        """Create a Stripe Checkout Session for a booking.

        Validates:
        - Booking exists and belongs to user
        - Booking is in PENDING state and not already paid
        - Amount comes from authoritative booking data
        - No duplicate active payment exists

        Returns dict with session details or error.
        """
        try:
            # Stripe is an optional module — return a clear config error if
            # credentials are absent instead of crashing or calling the API.
            if not PaymentService.is_configured():
                return {
                    "success": False,
                    "message": "Stripe is not configured. Payments are an optional future module; "
                               "confirm this booking directly instead.",
                    "session_id": None,
                    "checkout_url": None,
                }

            # 1. Fetch booking
            result = await session.execute(
                select(Booking).where(Booking.id == booking_id)
            )
            booking = result.scalars().first()

            if not booking:
                return {
                    "success": False,
                    "message": "Booking not found.",
                    "session_id": None,
                    "checkout_url": None,
                }

            # 2. Verify ownership
            if booking.user_id != user_id:
                return {
                    "success": False,
                    "message": "You do not own this booking.",
                    "session_id": None,
                    "checkout_url": None,
                }

            # 3. Check booking status — only PENDING bookings can be paid
            if booking.status != BookingStatus.PENDING:
                return {
                    "success": False,
                    "message": f"Booking is {booking.status.value}, cannot create payment.",
                    "session_id": None,
                    "checkout_url": None,
                }

            # 4. Check for existing active payment
            existing_payment_result = await session.execute(
                select(Payment).where(
                    (Payment.booking_id == booking_id)
                    & (Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.SUCCEEDED]))
                )
            )
            existing_payment = existing_payment_result.scalars().first()

            if existing_payment:
                # If payment already succeeded, booking should have been confirmed
                if existing_payment.status == PaymentStatus.SUCCEEDED:
                    return {
                        "success": False,
                        "message": "Payment already succeeded for this booking.",
                        "session_id": existing_payment.stripe_checkout_session_id,
                        "checkout_url": None,
                    }
                # If payment is pending, reuse it (idempotency)
                if existing_payment.stripe_checkout_session_id:
                    return {
                        "success": True,
                        "message": "Existing pending payment session retrieved.",
                        "session_id": existing_payment.stripe_checkout_session_id,
                        "checkout_url": f"https://checkout.stripe.com/pay/{existing_payment.stripe_checkout_session_id}",
                    }

            # 5. Get authoritative price from booking (never trust client)
            amount_cents = int(booking.total_amount * 100)  # Stripe uses cents
            currency = booking.currency.lower()

            # 6. Create Stripe Checkout Session
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency,
                                "product_data": {
                                    "name": f"Flight Booking - {booking.pnr}",
                                    "description": f"{booking.passenger_count} passenger(s)",
                                },
                                "unit_amount": amount_cents,
                            },
                            "quantity": 1,
                        }
                    ],
                    mode="payment",
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata={
                        "booking_id": booking_id,
                        "booking_pnr": booking.pnr,
                        "user_id": user_id,
                    },
                )
            except stripe.error.StripeError as e:
                return {
                    "success": False,
                    "message": f"Stripe error: {str(e)}",
                    "session_id": None,
                    "checkout_url": None,
                }

            # 7. Create or update Payment record
            payment_id = str(uuid.uuid4())
            payment = Payment(
                id=payment_id,
                booking_id=booking_id,
                amount=booking.total_amount,
                currency=currency.upper(),
                method=PaymentMethod.STRIPE,
                status=PaymentStatus.PENDING,
                stripe_checkout_session_id=checkout_session.id,
            )
            session.add(payment)
            await session.flush()

            return {
                "success": True,
                "message": "Checkout session created successfully.",
                "session_id": checkout_session.id,
                "checkout_url": checkout_session.url,
                "payment_id": payment_id,
            }

        except Exception as e:
            await session.rollback()
            return {
                "success": False,
                "message": f"Payment creation failed: {str(e)}",
                "session_id": None,
                "checkout_url": None,
            }

    @staticmethod
    async def verify_payment_from_webhook(
        session: AsyncSession,
        stripe_event: dict,
    ) -> Optional[dict]:
        """Verify Stripe webhook event and confirm booking if payment succeeded.

        Idempotent: processes the same event multiple times safely.

        Returns dict with verification result or None on error.
        """
        try:
            event_id = stripe_event.get("id")
            event_type = stripe_event.get("type")

            # Handle charge.succeeded event
            if event_type == "charge.succeeded":
                charge = stripe_event.get("data", {}).get("object", {})
                stripe_charge_id = charge.get("id")
                stripe_payment_intent_id = charge.get("payment_intent")

                # Get metadata from charge
                metadata = charge.get("metadata", {})
                booking_id = metadata.get("booking_id")
                user_id = metadata.get("user_id")

                if not booking_id or not user_id:
                    return {
                        "success": False,
                        "message": "Missing booking/user metadata in charge.",
                        "booking_id": None,
                    }

                # 1. Check for idempotency — has this event been processed?
                payment_result = await session.execute(
                    select(Payment).where(
                        Payment.stripe_event_id == event_id
                    )
                )
                payment = payment_result.scalars().first()

                if payment:
                    # Already processed this event
                    return {
                        "success": True,
                        "message": "Payment already verified (idempotent).",
                        "booking_id": booking_id,
                        "already_processed": True,
                    }

                # 2. Find or create Payment record
                payment_result = await session.execute(
                    select(Payment).where(
                        Payment.booking_id == booking_id
                    )
                )
                payment = payment_result.scalars().first()

                if not payment:
                    # Payment record should exist, but create if missing
                    payment_id = str(uuid.uuid4())
                    payment = Payment(
                        id=payment_id,
                        booking_id=booking_id,
                        amount=charge.get("amount", 0) / 100,  # Stripe cents → dollars
                        currency=charge.get("currency", "usd").upper(),
                        method=PaymentMethod.STRIPE,
                        status=PaymentStatus.PENDING,
                    )
                    session.add(payment)

                # 3. Update payment status to SUCCEEDED
                payment.status = PaymentStatus.SUCCEEDED
                payment.stripe_charge_id = stripe_charge_id
                payment.stripe_payment_intent_id = stripe_payment_intent_id
                payment.stripe_event_id = event_id
                payment.paid_at = utcnow()
                await session.flush()

                # 4. Confirm the booking using BookingService
                booking_confirm_response = await BookingService.confirm_booking(
                    session,
                    user_id=user_id,
                    booking_id=booking_id,
                )

                return {
                    "success": booking_confirm_response.success,
                    "message": f"Payment verified. Booking: {booking_confirm_response.message}",
                    "booking_id": booking_id,
                    "payment_status": PaymentStatus.SUCCEEDED.value,
                    "booking_confirmed": booking_confirm_response.success,
                }

            # Handle charge.failed event
            elif event_type == "charge.failed":
                charge = stripe_event.get("data", {}).get("object", {})
                stripe_charge_id = charge.get("id")
                metadata = charge.get("metadata", {})
                booking_id = metadata.get("booking_id")

                if not booking_id:
                    return {
                        "success": False,
                        "message": "Missing booking metadata in failed charge.",
                        "booking_id": None,
                    }

                # Find payment and mark as FAILED
                payment_result = await session.execute(
                    select(Payment).where(Payment.booking_id == booking_id)
                )
                payment = payment_result.scalars().first()

                if payment:
                    payment.status = PaymentStatus.FAILED
                    payment.stripe_charge_id = stripe_charge_id
                    payment.stripe_event_id = event_id
                    await session.flush()

                # Booking remains in PENDING state
                return {
                    "success": False,
                    "message": "Payment failed. Booking remains pending.",
                    "booking_id": booking_id,
                    "payment_status": PaymentStatus.FAILED.value,
                }

            else:
                # Unknown event type
                return {
                    "success": True,
                    "message": f"Event type '{event_type}' not handled.",
                    "booking_id": None,
                }

        except Exception as e:
            await session.rollback()
            return {
                "success": False,
                "message": f"Webhook verification failed: {str(e)}",
                "booking_id": None,
            }

    @staticmethod
    async def get_payment_status(
        session: AsyncSession,
        booking_id: str,
        user_id: str,
    ) -> Optional[dict]:
        """Retrieve payment status for a booking (with ownership check)."""
        try:
            # Verify ownership
            booking_result = await session.execute(
                select(Booking).where(Booking.id == booking_id)
            )
            booking = booking_result.scalars().first()

            if not booking:
                return {
                    "success": False,
                    "message": "Booking not found.",
                    "payment": None,
                }

            if booking.user_id != user_id:
                return {
                    "success": False,
                    "message": "You do not own this booking.",
                    "payment": None,
                }

            # Get payment
            payment_result = await session.execute(
                select(Payment).where(Payment.booking_id == booking_id)
            )
            payment = payment_result.scalars().first()

            if not payment:
                return {
                    "success": True,
                    "message": "No payment created yet for this booking.",
                    "payment": {
                        "status": "no_payment",
                        "booking_id": booking_id,
                    },
                }

            return {
                "success": True,
                "message": "Payment status retrieved.",
                "payment": {
                    "payment_id": payment.id,
                    "booking_id": booking_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "status": payment.status.value,
                    "created_at": payment.created_at.isoformat(),
                    "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Status retrieval failed: {str(e)}",
                "payment": None,
            }
