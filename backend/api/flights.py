"""
Phase 14 — Flight API Endpoints.

REST API for flight search, filtering, details, and price calculations.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from models.flight import CabinClass
from models.user import User
from services.flight_service import FlightService
from schemas.flights import (
    FlightSearchRequest,
    FlightFilterRequest,
    FlightResponse,
    PriceBreakdownResponse,
    SeatAvailabilityResponse,
)
from dependencies.auth import get_current_user


router = APIRouter(prefix="/api/flights", tags=["flights"])


def _flight_to_response(flight) -> FlightResponse:
    """Convert Flight ORM to response schema."""
    return FlightResponse(
        id=flight.id,
        flight_number=flight.flight_number,
        airline=flight.airline,
        airline_code=flight.airline_code,
        origin=flight.origin,
        destination=flight.destination,
        origin_city=flight.origin_city,
        destination_city=flight.destination_city,
        departure_time=flight.departure_time.isoformat(),
        arrival_time=flight.arrival_time.isoformat(),
        duration_minutes=flight.duration_minutes,
        stops=flight.stops,
        cabin_class=flight.cabin_class.value,
        base_price=flight.base_price,
        tax_percent=flight.tax_percent,
        available_seats=flight.available_seats,
        total_seats=flight.total_seats,
    )


@router.post("/search", response_model=List[FlightResponse])
async def search_flights(
    request: FlightSearchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for available flights.

    Query parameters:
    - origin: IATA code (e.g., KHI)
    - destination: IATA code (e.g., DXB)
    - date: ISO date (e.g., 2026-09-07)
    - cabin_class: economy|business|first (default: economy)

    Returns:
        List of available flights
    """
    try:
        cabin_class = CabinClass(request.cabin_class or "economy")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cabin class. Must be one of: {', '.join([c.value for c in CabinClass])}",
        )

    flights = await FlightService.search_flights(
        session,
        origin=request.origin,
        destination=request.destination,
        date=request.date,
        cabin_class=cabin_class,
    )

    return [_flight_to_response(f) for f in flights]


@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight_details(
    flight_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information for a specific flight.

    Args:
        flight_id: UUID of the flight

    Returns:
        FlightResponse with full flight details
    """
    flight = await FlightService.get_flight_details(session, flight_id)

    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight not found",
        )

    return _flight_to_response(flight)


@router.post("/filter", response_model=List[FlightResponse])
async def filter_flights(
    request: FlightFilterRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search and filter flights with advanced criteria.

    Filter options:
    - cabin_class: economy|business|first
    - max_stops: 0, 1, 2, ...
    - airline: airline code (e.g., EK)
    - min_price, max_price: price range
    - time_of_day: morning|afternoon|evening|night
    """
    try:
        cabin_class = CabinClass(request.cabin_class or "economy") if request.cabin_class else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cabin class",
        )

    flights = await FlightService.filter_flights(
        session,
        origin=request.origin,
        destination=request.destination,
        date=request.date,
        cabin_class=cabin_class,
        max_stops=request.max_stops,
        airline=request.airline,
        min_price=request.min_price,
        max_price=request.max_price,
        time_of_day=request.time_of_day,
    )

    return [_flight_to_response(f) for f in flights]


@router.post("/price", response_model=PriceBreakdownResponse)
async def calculate_price(
    flight_id: str = Query(..., description="Flight ID"),
    passenger_count: int = Query(..., ge=1, description="Number of passengers"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate total price for a given number of passengers.

    Args:
        flight_id: UUID of the flight
        passenger_count: Number of passengers (minimum 1)

    Returns:
        PriceBreakdownResponse with itemized pricing
    """
    flight = await FlightService.get_flight_details(session, flight_id)

    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight not found",
        )

    price_breakdown = FlightService.calculate_flight_price(flight, passenger_count)

    return PriceBreakdownResponse(
        flight_id=price_breakdown.flight_id,
        flight_number=price_breakdown.flight_number,
        passenger_count=price_breakdown.passenger_count,
        base_price_per_person=price_breakdown.base_price_per_person,
        tax_per_person=price_breakdown.tax_per_person,
        total_per_person=price_breakdown.total_per_person,
        grand_total=price_breakdown.grand_total,
        currency=price_breakdown.currency,
    )


@router.get("/{flight_id}/seats", response_model=SeatAvailabilityResponse)
async def get_seat_availability(
    flight_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get seat availability for a flight.

    Returns:
        SeatAvailabilityResponse with available and total seats
    """
    flight = await FlightService.get_flight_details(session, flight_id)

    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight not found",
        )

    return SeatAvailabilityResponse(
        flight_id=flight.id,
        flight_number=flight.flight_number,
        available_seats=flight.available_seats,
        total_seats=flight.total_seats,
    )
