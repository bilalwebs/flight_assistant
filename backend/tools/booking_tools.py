"""
Phase 12 — Booking Tools.

Thin wrappers around BookingService using @function_tool from Agents SDK.
"""
from typing import List, Optional
from pydantic import Field, BaseModel

from agents import function_tool
from database.database import AsyncSessionLocal
from services.booking_service import BookingService


class PassengerInfo(BaseModel):
    """Passenger information for booking."""
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    passport_number: Optional[str] = Field(None, description="Passport number")
    nationality: Optional[str] = Field(None, description="Nationality")
    passenger_type: str = Field(default="adult", description="adult, child, or infant")
    meal_preference: Optional[str] = Field(None, description="Meal preference")
    special_assistance: bool = Field(default=False, description="Special assistance needed")


@function_tool
async def create_booking(
    user_id: str = Field(..., description="User ID placing the booking"),
    flight_id: str = Field(..., description="Flight ID to book"),
    passengers: List[PassengerInfo] = Field(
        ...,
        description="List of passengers with first_name, last_name, date_of_birth (YYYY-MM-DD)"
    ),
    cabin_class: str = Field(default="economy", description="Cabin class: economy, premium_economy, business, first"),
    contact_email: str = Field(..., description="Email for booking confirmation"),
    contact_phone: Optional[str] = Field(None, description="Phone number for booking contact"),
    notes: Optional[str] = Field(None, description="Additional booking notes"),
) -> dict:
    """
    Create a new booking for a flight.

    Validates all inputs server-side:
    - Flight exists and has available seats
    - Passenger count is valid
    - Passenger information is complete and valid
    - Price is calculated server-side (never trusted from client)

    Returns a BookingResponse with PNR and booking details on success.
    """
    try:
        # Convert Pydantic models to dicts for BookingService
        passengers_list = [p.model_dump(exclude_none=True) for p in passengers]

        async with AsyncSessionLocal() as session:
            response = await BookingService.create_booking(
                session=session,
                user_id=user_id,
                flight_id=flight_id,
                passengers=passengers_list,
                cabin_class=cabin_class,
                contact_email=contact_email,
                contact_phone=contact_phone,
                notes=notes,
            )
            await session.commit()
            return response.model_dump()
    except Exception as e:
        return {
            "success": False,
            "pnr": "",
            "booking_id": "",
            "status": "",
            "total_amount": 0,
            "currency": "USD",
            "message": f"Tool error: {str(e)}",
        }


@function_tool
async def confirm_booking(
    user_id: str = Field(..., description="User ID confirming the booking"),
    booking_id: str = Field(..., description="Booking ID to confirm"),
) -> dict:
    """
    Confirm a pending booking.

    Only PENDING bookings can be confirmed.
    Transitions status from PENDING to CONFIRMED.
    """
    try:
        async with AsyncSessionLocal() as session:
            response = await BookingService.confirm_booking(
                session=session,
                user_id=user_id,
                booking_id=booking_id,
            )
            await session.commit()
            return response.model_dump()
    except Exception as e:
        return {
            "success": False,
            "pnr": "",
            "booking_id": "",
            "status": "",
            "total_amount": 0,
            "currency": "USD",
            "message": f"Tool error: {str(e)}",
        }


@function_tool
async def get_booking(
    user_id: str = Field(..., description="User ID retrieving the booking"),
    pnr: str = Field(..., description="Booking reference (PNR) to retrieve"),
) -> dict:
    """
    Retrieve booking details by PNR.

    Only the booking owner can retrieve their booking.
    Returns booking details including flight info, passengers, and total price.
    """
    try:
        async with AsyncSessionLocal() as session:
            booking = await BookingService.get_booking(
                session=session,
                user_id=user_id,
                pnr=pnr,
            )
            if not booking:
                return {
                    "success": False,
                    "message": "Booking not found or you do not have permission to view it.",
                    "booking": None,
                }
            return {
                "success": True,
                "message": "Booking retrieved successfully.",
                "booking": booking.model_dump(),
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Tool error: {str(e)}",
            "booking": None,
        }


@function_tool
async def list_user_bookings(
    user_id: str = Field(..., description="User ID to list bookings for"),
) -> dict:
    """
    List all bookings for a user.

    Returns a list of the user's bookings ordered by creation date (newest first).
    """
    try:
        async with AsyncSessionLocal() as session:
            bookings = await BookingService.list_user_bookings(
                session=session,
                user_id=user_id,
            )
            return {
                "success": True,
                "message": f"Found {len(bookings)} booking(s).",
                "bookings": [b.model_dump() for b in bookings],
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Tool error: {str(e)}",
            "bookings": [],
        }


@function_tool
async def cancel_booking(
    user_id: str = Field(..., description="User ID cancelling the booking"),
    booking_id: str = Field(..., description="Booking ID to cancel"),
    reason: Optional[str] = Field(None, description="Reason for cancellation"),
) -> dict:
    """
    Cancel a booking.

    Only the booking owner can cancel their booking.
    PENDING and CONFIRMED bookings can be cancelled.
    Cancelled bookings have their seats restored to the flight.
    """
    try:
        async with AsyncSessionLocal() as session:
            response = await BookingService.cancel_booking(
                session=session,
                user_id=user_id,
                booking_id=booking_id,
                reason=reason,
            )
            await session.commit()
            return response.model_dump()
    except Exception as e:
        return {
            "success": False,
            "pnr": "",
            "booking_id": "",
            "status": "",
            "total_amount": 0,
            "currency": "USD",
            "message": f"Tool error: {str(e)}",
        }

