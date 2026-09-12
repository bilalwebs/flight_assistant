"""
Phase 12 — Booking Service.

Business logic for booking operations: creation, confirmation, retrieval, cancellation.
Handles state transitions, validation, and database transactions.
"""
import uuid
import secrets
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from models.booking import Booking, BookingStatus, Passenger, PassengerType
from models.flight import Flight
from models.user import User
from models.responses import BookingSchema, PassengerSchema, BookingResponse
from services.flight_service import FlightService
from utils.datetime_utils import utcnow


class BookingService:
    """Business logic for booking operations."""

    @staticmethod
    def _generate_pnr() -> str:
        """Generate a unique, non-predictable booking reference (PNR).

        Format: 6 uppercase alphanumeric characters (e.g., AB1CD2).
        Returns immediately; does not check database for uniqueness —
        the database unique constraint provides that guarantee.
        """
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(chars) for _ in range(6))

    @staticmethod
    async def create_booking(
        session: AsyncSession,
        user_id: str,
        flight_id: str,
        passengers: List[dict],
        cabin_class: str = "economy",
        contact_email: str = "",
        contact_phone: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> BookingResponse:
        """Create a new booking with passengers.

        Validates:
        - Flight exists and is bookable
        - Requested passenger count is valid
        - Enough seats available
        - Passenger information is valid
        - Price calculated server-side

        Returns BookingResponse with success/failure and details.
        """
        try:
            # 1. Verify user exists
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalars().first()
            if not user:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="User not found.",
                )

            # 2. Verify flight exists and is bookable
            flight = await FlightService.get_flight_details(session, flight_id)
            if not flight:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="Flight not found.",
                )

            # 3. Validate passenger count
            if not passengers or len(passengers) == 0:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="At least one passenger is required.",
                )

            passenger_count = len(passengers)

            # 4. Check seat availability
            if not FlightService.check_seat_availability(flight, passenger_count):
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message=f"Insufficient seats available. Only {flight.available_seats} seat(s) remaining.",
                )

            # 5. Validate each passenger
            for p in passengers:
                validation_error = BookingService._validate_passenger(p)
                if validation_error:
                    return BookingResponse(
                        success=False,
                        pnr="",
                        booking_id="",
                        status="",
                        total_amount=0,
                        currency="USD",
                        message=f"Invalid passenger data: {validation_error}",
                    )

            # 6. Calculate price server-side (never trust client price)
            price_breakdown = FlightService.calculate_flight_price(flight, passenger_count)
            base_amount = price_breakdown.base_price_per_person * passenger_count
            tax_amount = price_breakdown.tax_per_person * passenger_count
            total_amount = price_breakdown.grand_total

            # 7. Generate unique PNR
            pnr = BookingService._generate_pnr()

            # 8. Create booking record
            booking_id = str(uuid.uuid4())
            booking = Booking(
                id=booking_id,
                pnr=pnr,
                user_id=user_id,
                flight_id=flight_id,
                cabin_class=cabin_class,
                status=BookingStatus.PENDING,
                passenger_count=passenger_count,
                base_amount=base_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                currency="USD",
                contact_email=contact_email,
                contact_phone=contact_phone,
                notes=notes,
            )
            session.add(booking)

            # 9. Create passenger records (cascade within transaction)
            for p in passengers:
                passenger_id = str(uuid.uuid4())
                passenger = Passenger(
                    id=passenger_id,
                    booking_id=booking_id,
                    first_name=p["first_name"],
                    last_name=p["last_name"],
                    date_of_birth=p["date_of_birth"],
                    passport_number=p.get("passport_number"),
                    nationality=p.get("nationality"),
                    passenger_type=p.get("passenger_type", "adult"),
                    meal_preference=p.get("meal_preference"),
                    special_assistance=p.get("special_assistance", False),
                )
                session.add(passenger)

            # 10. Reduce available seats
            flight.available_seats -= passenger_count

            await session.flush()

            return BookingResponse(
                success=True,
                pnr=pnr,
                booking_id=booking_id,
                status=BookingStatus.PENDING.value,
                total_amount=total_amount,
                currency="USD",
                message=f"Booking created successfully. PNR: {pnr}",
            )

        except IntegrityError as e:
            await session.rollback()
            if "pnr" in str(e).lower():
                # PNR collision (extremely rare) — retry with new PNR
                return await BookingService.create_booking(
                    session,
                    user_id,
                    flight_id,
                    passengers,
                    cabin_class,
                    contact_email,
                    contact_phone,
                    notes,
                )
            return BookingResponse(
                success=False,
                pnr="",
                booking_id="",
                status="",
                total_amount=0,
                currency="USD",
                message="Database integrity error. Please try again.",
            )
        except Exception as e:
            await session.rollback()
            return BookingResponse(
                success=False,
                pnr="",
                booking_id="",
                status="",
                total_amount=0,
                currency="USD",
                message=f"Booking creation failed: {str(e)}",
            )

    @staticmethod
    def _validate_passenger(passenger: dict) -> Optional[str]:
        """Validate passenger data. Returns error message if invalid, None if valid."""
        required = ["first_name", "last_name", "date_of_birth"]
        for field in required:
            if field not in passenger or not str(passenger[field]).strip():
                return f"Missing required field: {field}"

        first_name = str(passenger["first_name"]).strip()
        last_name = str(passenger["last_name"]).strip()
        date_of_birth = str(passenger["date_of_birth"]).strip()

        if len(first_name) == 0 or len(first_name) > 100:
            return "First name must be 1-100 characters."
        if len(last_name) == 0 or len(last_name) > 100:
            return "Last name must be 1-100 characters."

        if not BookingService._is_valid_date(date_of_birth):
            return "Date of birth must be in YYYY-MM-DD format."

        return None

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Validate date string in YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    async def confirm_booking(
        session: AsyncSession,
        user_id: str,
        booking_id: str,
    ) -> BookingResponse:
        """Confirm a pending booking. Transitions PENDING → CONFIRMED."""
        try:
            # Fetch booking and verify ownership
            booking = await BookingService._get_booking_by_id(session, booking_id)
            if not booking:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="Booking not found.",
                )

            if booking.user_id != user_id:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="You do not own this booking.",
                )

            # Check state transition validity
            if booking.status != BookingStatus.PENDING:
                return BookingResponse(
                    success=False,
                    pnr=booking.pnr,
                    booking_id=booking_id,
                    status=booking.status.value,
                    total_amount=booking.total_amount,
                    currency="USD",
                    message=f"Only PENDING bookings can be confirmed. Current status: {booking.status.value}",
                )

            # Verify flight still has passengers' seats
            flight = booking.flight
            if flight.available_seats < 0:
                # Seats were freed elsewhere (shouldn't happen, but safeguard)
                await session.rollback()
                return BookingResponse(
                    success=False,
                    pnr=booking.pnr,
                    booking_id=booking_id,
                    status=booking.status.value,
                    total_amount=booking.total_amount,
                    currency="USD",
                    message="Flight availability changed. Confirmation failed.",
                )

            # Transition to CONFIRMED
            booking.status = BookingStatus.CONFIRMED
            booking.updated_at = utcnow()
            await session.flush()

            return BookingResponse(
                success=True,
                pnr=booking.pnr,
                booking_id=booking_id,
                status=BookingStatus.CONFIRMED.value,
                total_amount=booking.total_amount,
                currency="USD",
                message=f"Booking {booking.pnr} confirmed successfully.",
            )

        except Exception as e:
            await session.rollback()
            return BookingResponse(
                success=False,
                pnr="",
                booking_id="",
                status="",
                total_amount=0,
                currency="USD",
                message=f"Confirmation failed: {str(e)}",
            )

    @staticmethod
    async def get_booking(
        session: AsyncSession,
        user_id: str,
        pnr: str,
    ) -> Optional[BookingSchema]:
        """Retrieve booking by PNR with ownership verification."""
        try:
            result = await session.execute(
                select(Booking).where(Booking.pnr == pnr.upper())
            )
            booking = result.scalars().first()
            if not booking:
                return None

            # Verify ownership
            if booking.user_id != user_id:
                return None

            return BookingSchema.model_validate(booking)
        except Exception:
            return None

    @staticmethod
    async def list_user_bookings(
        session: AsyncSession,
        user_id: str,
    ) -> List[BookingSchema]:
        """List all bookings for a user."""
        try:
            result = await session.execute(
                select(Booking)
                .where(Booking.user_id == user_id)
                .order_by(Booking.created_at.desc())
            )
            bookings = result.scalars().all()
            return [BookingSchema.model_validate(b) for b in bookings]
        except Exception:
            return []

    @staticmethod
    async def cancel_booking(
        session: AsyncSession,
        user_id: str,
        booking_id: str,
        reason: Optional[str] = None,
    ) -> BookingResponse:
        """Cancel a booking and restore seats. Transitions PENDING/CONFIRMED → CANCELLED."""
        try:
            booking = await BookingService._get_booking_by_id(session, booking_id)
            if not booking:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="Booking not found.",
                )

            # Verify ownership
            if booking.user_id != user_id:
                return BookingResponse(
                    success=False,
                    pnr="",
                    booking_id="",
                    status="",
                    total_amount=0,
                    currency="USD",
                    message="You do not own this booking.",
                )

            # Check state transition validity
            if booking.status == BookingStatus.CANCELLED:
                return BookingResponse(
                    success=False,
                    pnr=booking.pnr,
                    booking_id=booking_id,
                    status=booking.status.value,
                    total_amount=booking.total_amount,
                    currency="USD",
                    message="Booking is already cancelled.",
                )

            if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
                return BookingResponse(
                    success=False,
                    pnr=booking.pnr,
                    booking_id=booking_id,
                    status=booking.status.value,
                    total_amount=booking.total_amount,
                    currency="USD",
                    message=f"Cannot cancel booking in {booking.status.value} status.",
                )

            # Restore seats
            flight = booking.flight
            flight.available_seats += booking.passenger_count

            # Transition to CANCELLED
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = utcnow()
            booking.cancellation_reason = reason or "User-initiated cancellation"
            booking.updated_at = utcnow()

            await session.flush()

            return BookingResponse(
                success=True,
                pnr=booking.pnr,
                booking_id=booking_id,
                status=BookingStatus.CANCELLED.value,
                total_amount=booking.total_amount,
                currency="USD",
                message=f"Booking {booking.pnr} cancelled successfully. Seats restored.",
            )

        except Exception as e:
            await session.rollback()
            return BookingResponse(
                success=False,
                pnr="",
                booking_id="",
                status="",
                total_amount=0,
                currency="USD",
                message=f"Cancellation failed: {str(e)}",
            )

    @staticmethod
    async def get_user_bookings(
        session: AsyncSession,
        user_id: str,
    ) -> List[Booking]:
        """Get all bookings for a user (for API layer)."""
        try:
            result = await session.execute(
                select(Booking)
                .where(Booking.user_id == user_id)
                .order_by(Booking.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception:
            return []

    @staticmethod
    async def get_booking_by_pnr(
        session: AsyncSession,
        pnr: str,
    ) -> Optional[Booking]:
        """Get booking by PNR (for API layer, no ownership check — caller enforces)."""
        try:
            result = await session.execute(
                select(Booking).where(Booking.pnr == pnr.upper())
            )
            return result.scalars().first()
        except Exception:
            return None

    @staticmethod
    async def _get_booking_by_id(
        session: AsyncSession,
        booking_id: str,
    ) -> Optional[Booking]:
        """Internal helper: fetch booking by ID without ownership check."""
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        return result.scalars().first()
