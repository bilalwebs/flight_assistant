"""
OpenAI Agents SDK function tools for Flight operations.
These tools wrap the FlightService and expose it to AI agents.
"""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import Field

from agents import function_tool
from database.database import AsyncSessionLocal
from services.flight_service import FlightService
from models.flight import CabinClass
from models.responses import FlightSearchResult, FlightSchema, PriceBreakdown

# Note: In a full agentic loop, these tools would ideally receive the DB session
# through context or a dependency injection mechanism. For Phase 4, we manage
# the session inside the tools to ensure they are runnable for testing.

@function_tool
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    cabin_class: str = "economy"
) -> dict:
    """
    Search for available flights based on route, date, and cabin class.

    Args:
        origin: 3-letter IATA code of the origin city (e.g., KHI, LHE, ISB)
        destination: 3-letter IATA code of the destination city (e.g., DXB, IST, DOH)
        departure_date: Date in YYYY-MM-DD format
        passengers: Number of travelers (default: 1)
        cabin_class: One of: economy, premium_economy, business, first
    """
    try:
        date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
        cabin_enum = CabinClass(cabin_class.lower())

        async with AsyncSessionLocal() as session:
            flights = await FlightService.search_flights(
                session, origin, destination, date_obj, cabin_enum
            )

            # Convert ORM to Pydantic for serialization
            flight_schemas = [FlightSchema.model_validate(f) for f in flights]

            result = FlightSearchResult(
                flights=flight_schemas,
                total_found=len(flight_schemas),
                origin=origin.upper(),
                destination=destination.upper(),
                search_date=departure_date,
                message=f"Found {len(flight_schemas)} flights." if flight_schemas else "No flights found for this route and date."
            )
            return result.model_dump()
    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}", "success": False}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}", "success": False}

@function_tool
async def get_flight_details(flight_id: str) -> dict:
    """
    Retrieve full details for a specific flight by its ID.
    """
    try:
        async with AsyncSessionLocal() as session:
            flight = await FlightService.get_flight_details(session, flight_id)
            if not flight:
                return {"error": "Flight not found", "success": False}

            return FlightSchema.model_validate(flight).model_dump()
    except Exception as e:
        return {"error": str(e), "success": False}

@function_tool
async def find_flight_by_number(flight_number: str) -> dict:
    """
    Look up a specific flight by its flight NUMBER (e.g., "EK-601", "PK-201").

    Use this when the user references a flight by its number rather than an
    internal id. Returns the flight's real details straight from the database,
    or a clean not-found result. Never fabricates a flight.

    Args:
        flight_number: The airline flight number, e.g. "EK-601".
    """
    try:
        async with AsyncSessionLocal() as session:
            flight = await FlightService.get_flight_by_number(session, flight_number)
            if not flight:
                return {"error": "Flight not found", "success": False}

            return FlightSchema.model_validate(flight).model_dump()
    except Exception as e:
        return {"error": str(e), "success": False}

@function_tool
async def filter_flights(
    origin: str,
    destination: str,
    departure_date: str,
    max_stops: Optional[int] = None,
    airline: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    time_of_day: Optional[str] = None,
    cabin_class: str = "economy"
) -> dict:
    """
    Filter available flights using advanced criteria like price, stops, airline, and time.

    Args:
        origin: IATA code
        destination: IATA code
        departure_date: YYYY-MM-DD
        max_stops: Maximum number of stops (0 for direct)
        airline: Specific airline name
        min_price: Minimum base price
        max_price: Maximum base price
        time_of_day: One of: morning, afternoon, evening, night
        cabin_class: economy, business, etc.
    """
    try:
        date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
        cabin_enum = CabinClass(cabin_class.lower())

        async with AsyncSessionLocal() as session:
            flights = await FlightService.filter_flights(
                session, origin, destination, date_obj, cabin_enum,
                max_stops, airline, min_price, max_price, time_of_day
            )

            flight_schemas = [FlightSchema.model_validate(f) for f in flights]
            return {
                "flights": [f.model_dump() for f in flight_schemas],
                "count": len(flight_schemas)
            }
    except Exception as e:
        return {"error": str(e), "success": False}

@function_tool
async def compare_flights(flight_ids: List[str]) -> dict:
    """
    Compare multiple flights by their IDs to help the user choose.
    """
    try:
        async with AsyncSessionLocal() as session:
            flights = []
            for fid in flight_ids:
                f = await FlightService.get_flight_details(session, fid)
                if f:
                    flights.append(f)

            if not flights:
                return {"error": "No valid flights found for comparison", "success": False}

            comparison = FlightService.compare_flights(flights)
            return {"comparison": comparison, "count": len(comparison)}
    except Exception as e:
        return {"error": str(e), "success": False}

@function_tool
async def calculate_flight_price(flight_id: str, passengers: int = 1) -> dict:
    """
    Calculate the total price for a flight including taxes for a specific number of passengers.
    """
    try:
        if passengers < 1:
            return {"error": "Passenger count must be at least 1", "success": False}

        async with AsyncSessionLocal() as session:
            flight = await FlightService.get_flight_details(session, flight_id)
            if not flight:
                return {"error": "Flight not found", "success": False}

            breakdown = FlightService.calculate_flight_price(flight, passengers)
            return breakdown.model_dump()
    except Exception as e:
        return {"error": str(e), "success": False}

@function_tool
async def check_seat_availability(flight_id: str, requested_seats: int = 1) -> dict:
    """
    Check if a specific number of seats are available on a flight.
    """
    try:
        async with AsyncSessionLocal() as session:
            flight = await FlightService.get_flight_details(session, flight_id)
            if not flight:
                return {"error": "Flight not found", "success": False}

            available = FlightService.check_seat_availability(flight, requested_seats)
            return {
                "flight_id": flight_id,
                "flight_number": flight.flight_number,
                "requested_seats": requested_seats,
                "available": available,
                "remaining_seats": flight.available_seats
            }
    except Exception as e:
        return {"error": str(e), "success": False}
