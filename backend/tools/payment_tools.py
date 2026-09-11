"""
Phase 13 — Payment Tools.

Thin wrappers around PaymentService using @function_tool from Agents SDK.
"""
from typing import Optional
from pydantic import Field

from agents import function_tool
from database.database import AsyncSessionLocal
from services.payment_service import PaymentService


@function_tool
async def create_payment(
    booking_id: str = Field(..., description="Booking ID to create payment for"),
    user_id: str = Field(..., description="User ID (for ownership verification)"),
    success_url: Optional[str] = Field(
        None,
        description="URL to redirect after successful payment"
    ),
    cancel_url: Optional[str] = Field(
        None,
        description="URL to redirect if payment is cancelled"
    ),
) -> dict:
    """
    Create a Stripe Checkout Session for a booking.

    Validates booking ownership and status.
    Returns checkout session URL for the user to complete payment.

    IMPORTANT: This does NOT charge the card or confirm the booking.
    Only a verified Stripe webhook event can confirm the booking.
    """
    try:
        async with AsyncSessionLocal() as session:
            response = await PaymentService.create_payment(
                session,
                booking_id=booking_id,
                user_id=user_id,
                success_url=success_url or "http://localhost:3000/payment/success",
                cancel_url=cancel_url or "http://localhost:3000/payment/cancel",
            )
            await session.commit()
            return response
    except Exception as e:
        return {
            "success": False,
            "message": f"Tool error: {str(e)}",
            "session_id": None,
            "checkout_url": None,
        }


@function_tool
async def get_payment_status(
    booking_id: str = Field(..., description="Booking ID to check payment status for"),
    user_id: str = Field(..., description="User ID (for ownership verification)"),
) -> dict:
    """
    Get payment status for a booking.

    Returns current payment status: pending, succeeded, or failed.
    Only the booking owner can retrieve payment status.
    """
    try:
        async with AsyncSessionLocal() as session:
            response = await PaymentService.get_payment_status(
                session,
                booking_id=booking_id,
                user_id=user_id,
            )
            return response
    except Exception as e:
        return {
            "success": False,
            "message": f"Tool error: {str(e)}",
            "payment": None,
        }
