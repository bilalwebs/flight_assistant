"""
Phase 14 — Booking API Endpoints.

REST API for flight booking operations with authenticated user ownership enforcement.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from models.user import User
from services.booking_service import BookingService
from schemas.bookings import (
    BookingCreateRequest,
    BookingResponse,
    BookingListResponse,
)
from dependencies.auth import get_current_user


router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def _booking_to_response(booking) -> BookingResponse:
    """Convert Booking ORM to response schema."""
    return BookingResponse(
        id=booking.id,
        pnr=booking.pnr,
        user_id=booking.user_id,
        flight_id=booking.flight_id,
        status=booking.status.value,
        cabin_class=booking.cabin_class,
        passenger_count=booking.passenger_count,
        base_amount=booking.base_amount,
        tax_amount=booking.tax_amount,
        total_amount=booking.total_amount,
        currency=booking.currency,
        contact_email=booking.contact_email,
        contact_phone=booking.contact_phone,
        created_at=booking.created_at.isoformat(),
        updated_at=booking.updated_at.isoformat(),
    )


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new flight booking.

    Validates:
    - Flight exists and is bookable
    - Sufficient seats available
    - Passenger data valid
    - Price calculated server-side (never trusts client)

    Returns:
        BookingResponse with authoritative booking details and PNR
    """
    # CRITICAL: Use authenticated user's ID, never trust client request
    # Convert Pydantic passenger models to dicts — BookingService expects dicts.
    passengers = [p.model_dump(exclude_none=True) for p in request.passengers]
    booking_response = await BookingService.create_booking(
        session,
        user_id=current_user.id,  # From authentication token
        flight_id=request.flight_id,
        passengers=passengers,
        cabin_class=request.cabin_class or "economy",
        contact_email=request.contact_email or current_user.email,
        contact_phone=request.contact_phone,
        notes=request.notes,
    )

    if not booking_response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=booking_response.message,
        )

    # Re-fetch the persisted booking so response reflects authoritative
    # base_amount / tax_amount / timestamps rather than approximating them.
    booking = await BookingService.get_booking_by_pnr(session, booking_response.pnr)
    await session.commit()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Booking was created but could not be retrieved.",
        )

    return _booking_to_response(booking)


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    List all bookings for the authenticated user.

    Returns only bookings owned by the current user (ownership enforced at service layer).

    Returns:
        BookingListResponse with user's bookings
    """
    bookings = await BookingService.get_user_bookings(session, current_user.id)

    return BookingListResponse(
        count=len(bookings),
        bookings=[_booking_to_response(b) for b in bookings],
    )


@router.get("/{pnr}", response_model=BookingResponse)
async def get_booking(
    pnr: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve a booking by PNR.

    CRITICAL: Enforces user ownership — a user can only retrieve their own bookings.

    Args:
        pnr: Booking reference number

    Returns:
        BookingResponse with booking details

    Raises:
        404: Booking not found
        403: Not authorized (booking belongs to different user)
    """
    booking = await BookingService.get_booking_by_pnr(session, pnr)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # CRITICAL: Enforce ownership
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this booking",
        )

    return _booking_to_response(booking)


@router.post("/{pnr}/confirm", response_model=BookingResponse)
async def confirm_booking(
    pnr: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Confirm a pending booking.

    CURRENT MVP FLOW: A pending booking is confirmed directly here
    (PENDING -> CONFIRMED) — no payment is required.
    FUTURE STRIPE FLOW: With the optional payment module enabled, a booking may
    also be confirmed after a verified Stripe webhook payment success.

    Args:
        pnr: Booking reference number

    Returns:
        BookingResponse with updated booking

    Raises:
        404: Booking not found
        403: Not authorized
        400: Cannot confirm booking in current state
    """
    booking = await BookingService.get_booking_by_pnr(session, pnr)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # CRITICAL: Enforce ownership
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to confirm this booking",
        )

    confirm_response = await BookingService.confirm_booking(
        session,
        user_id=current_user.id,
        booking_id=booking.id,
    )

    if not confirm_response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=confirm_response.message,
        )

    await session.commit()
    return _booking_to_response(booking)


@router.post("/{pnr}/cancel", response_model=BookingResponse)
async def cancel_booking(
    pnr: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Cancel a booking.

    CRITICAL: Only booking owner can cancel their own booking.

    Args:
        pnr: Booking reference number

    Returns:
        BookingResponse with cancelled booking

    Raises:
        404: Booking not found
        403: Not authorized
        400: Cannot cancel booking in current state
    """
    booking = await BookingService.get_booking_by_pnr(session, pnr)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # CRITICAL: Enforce ownership
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this booking",
        )

    cancel_response = await BookingService.cancel_booking(
        session,
        user_id=current_user.id,
        booking_id=booking.id,
    )

    if not cancel_response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=cancel_response.message,
        )

    await session.commit()
    return _booking_to_response(booking)
