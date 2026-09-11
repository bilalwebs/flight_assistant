"""
Phase 14 — Booking API Schemas.

Pydantic models for booking API requests and responses.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class PassengerInfo(BaseModel):
    """Passenger information."""
    first_name: str = Field(..., min_length=1, description="First name")
    last_name: str = Field(..., min_length=1, description="Last name")
    passenger_type: str = Field(..., description="Type: adult|child|infant")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "passenger_type": "adult",
                "date_of_birth": "1990-01-01"
            }
        }
    }


class BookingCreateRequest(BaseModel):
    """Create booking request."""
    flight_id: str = Field(..., description="Flight ID (UUID)")
    passengers: List[PassengerInfo] = Field(..., min_items=1, description="List of passengers")
    cabin_class: Optional[str] = Field("economy", description="Cabin class: economy|business|first")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email (defaults to user email)")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    notes: Optional[str] = Field(None, description="Additional notes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "flight_id": "550e8400-e29b-41d4-a716-446655440000",
                "passengers": [
                    {
                        "first_name": "John",
                        "last_name": "Doe",
                        "passenger_type": "adult",
                        "date_of_birth": "1990-01-01"
                    }
                ],
                "cabin_class": "economy",
                "contact_email": "john@example.com",
                "contact_phone": "+1234567890",
                "notes": "Special seating request"
            }
        }
    }


class BookingResponse(BaseModel):
    """Booking details response."""
    id: str = Field(..., description="Booking ID (UUID)")
    pnr: str = Field(..., description="Booking reference number")
    user_id: str = Field(..., description="User ID")
    flight_id: str = Field(..., description="Flight ID")
    status: str = Field(..., description="Booking status: pending|confirmed|cancelled")
    cabin_class: str = Field(..., description="Cabin class booked")
    passenger_count: int = Field(..., ge=1, description="Number of passengers")
    base_amount: float = Field(..., ge=0, description="Base amount before tax")
    tax_amount: float = Field(..., ge=0, description="Tax amount")
    total_amount: float = Field(..., ge=0, description="Total amount")
    currency: str = Field(..., description="Currency code")
    contact_email: str = Field(..., description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pnr": "ABC123",
                "user_id": "user-id-uuid",
                "flight_id": "flight-id-uuid",
                "status": "pending",
                "cabin_class": "economy",
                "passenger_count": 2,
                "base_amount": 300.0,
                "tax_amount": 45.0,
                "total_amount": 345.0,
                "currency": "USD",
                "contact_email": "john@example.com",
                "contact_phone": "+1234567890",
                "created_at": "2026-09-06T04:00:00Z",
                "updated_at": "2026-09-06T04:00:00Z"
            }
        }
    }


class BookingListResponse(BaseModel):
    """List of bookings response."""
    count: int = Field(..., ge=0, description="Number of bookings")
    bookings: List[BookingResponse] = Field(..., description="List of bookings")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 2,
                "bookings": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "pnr": "ABC123",
                        "user_id": "user-id-uuid",
                        "flight_id": "flight-id-uuid",
                        "status": "confirmed",
                        "cabin_class": "economy",
                        "passenger_count": 1,
                        "base_amount": 150.0,
                        "tax_amount": 22.5,
                        "total_amount": 172.5,
                        "currency": "USD",
                        "contact_email": "john@example.com",
                        "contact_phone": None,
                        "created_at": "2026-09-06T04:00:00Z",
                        "updated_at": "2026-09-06T04:00:00Z"
                    }
                ]
            }
        }
    }
