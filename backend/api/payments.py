"""
Phase 14 — Payment API Endpoints.

REST API for payment operations with authenticated user ownership enforcement.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from models.user import User
from services.payment_service import PaymentService
from schemas.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutResponse,
    PaymentStatusResponse,
)
from dependencies.auth import get_current_user


router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/checkout", response_model=PaymentCheckoutResponse)
async def create_payment_checkout(
    request: PaymentCheckoutRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for a booking.

    CRITICAL: Uses authenticated user's ID for ownership verification.
    Payment amount comes from authoritative booking data (never client-provided).

    Args:
        request: Payment checkout request with booking_id

    Returns:
        PaymentCheckoutResponse with Stripe checkout URL

    Raises:
        404: Booking not found
        400: Booking not in PENDING state or other validation error
        403: User does not own booking
    """
    response = await PaymentService.create_payment(
        session,
        booking_id=request.booking_id,
        user_id=current_user.id,  # From authentication token
        success_url=request.success_url or "http://localhost:3000/payment/success",
        cancel_url=request.cancel_url or "http://localhost:3000/payment/cancel",
    )

    if not response["success"]:
        # Determine appropriate status code based on error message
        if "not configured" in response["message"].lower():
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif "not found" in response["message"].lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "own" in response["message"].lower() or "not authorized" in response["message"].lower():
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=response["message"],
        )

    await session.commit()

    return PaymentCheckoutResponse(
        success=True,
        session_id=response.get("session_id"),
        checkout_url=response.get("checkout_url"),
        payment_id=response.get("payment_id"),
    )


@router.get("/{booking_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve payment status for a booking.

    CRITICAL: Only booking owner can retrieve payment status.

    Args:
        booking_id: Booking ID (UUID)

    Returns:
        PaymentStatusResponse with payment details

    Raises:
        404: Booking not found
        403: User does not own booking
    """
    response = await PaymentService.get_payment_status(
        session,
        booking_id=booking_id,
        user_id=current_user.id,  # From authentication token
    )

    if not response["success"]:
        if "not found" in response["message"].lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "own" in response["message"].lower() or "not authorized" in response["message"].lower():
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=response["message"],
        )

    payment = response.get("payment", {})

    return PaymentStatusResponse(
        success=True,
        booking_id=booking_id,
        payment_id=payment.get("payment_id"),
        status=payment.get("status"),
        amount=payment.get("amount"),
        currency=payment.get("currency"),
        created_at=payment.get("created_at"),
        paid_at=payment.get("paid_at"),
    )
