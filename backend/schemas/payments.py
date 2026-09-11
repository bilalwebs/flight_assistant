"""
Phase 14 — Payment API Schemas.

Pydantic models for payment API requests and responses.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class PaymentCheckoutRequest(BaseModel):
    """Create Stripe Checkout Session request."""
    booking_id: str = Field(..., description="Booking ID (UUID)")
    success_url: Optional[HttpUrl] = Field(
        None,
        description="URL to redirect after successful payment (defaults to localhost:3000/payment/success)"
    )
    cancel_url: Optional[HttpUrl] = Field(
        None,
        description="URL to redirect if payment is cancelled (defaults to localhost:3000/payment/cancel)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "booking_id": "550e8400-e29b-41d4-a716-446655440000",
                "success_url": "https://example.com/payment/success",
                "cancel_url": "https://example.com/payment/cancel"
            }
        }
    }


class PaymentCheckoutResponse(BaseModel):
    """Stripe Checkout Session response."""
    success: bool = Field(..., description="Whether checkout session was created successfully")
    session_id: Optional[str] = Field(None, description="Stripe Checkout Session ID")
    checkout_url: Optional[str] = Field(None, description="Stripe Checkout URL for user to complete payment")
    payment_id: Optional[str] = Field(None, description="Payment record ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "session_id": "cs_test_123456",
                "checkout_url": "https://checkout.stripe.com/pay/cs_test_123456",
                "payment_id": "payment-id-uuid"
            }
        }
    }


class PaymentStatusResponse(BaseModel):
    """Payment status response."""
    success: bool = Field(..., description="Whether status retrieval was successful")
    booking_id: str = Field(..., description="Booking ID")
    payment_id: Optional[str] = Field(None, description="Payment ID")
    status: Optional[str] = Field(None, description="Payment status: pending|succeeded|failed|no_payment")
    amount: Optional[float] = Field(None, ge=0, description="Payment amount")
    currency: Optional[str] = Field(None, description="Currency code")
    created_at: Optional[str] = Field(None, description="Payment creation timestamp")
    paid_at: Optional[str] = Field(None, description="Payment completion timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "booking_id": "550e8400-e29b-41d4-a716-446655440000",
                "payment_id": "payment-id-uuid",
                "status": "pending",
                "amount": 172.5,
                "currency": "USD",
                "created_at": "2026-09-06T04:00:00Z",
                "paid_at": None
            }
        }
    }
