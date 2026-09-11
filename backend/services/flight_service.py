"""
Business logic layer for Flight operations.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.flight import Flight, CabinClass, FlightStatus
from models.responses import FlightSchema, PriceBreakdown

class FlightService:
    @staticmethod
    async def search_flights(
        session: AsyncSession,
        origin: str,
        destination: str,
        date: datetime,
        cabin_class: CabinClass = CabinClass.ECONOMY
    ) -> List[Flight]:
        """Search for available flights based on route and date."""
        # Truncate time to match date filtering if needed,
        # but for now we look for flights on the specific day
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)

        query = select(Flight).where(
            and_(
                Flight.origin == origin.upper(),
                Flight.destination == destination.upper(),
                Flight.departure_time >= start,
                Flight.departure_time <= end,
                Flight.cabin_class == cabin_class,
                Flight.is_active == True,
                Flight.status == FlightStatus.SCHEDULED
            )
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_flight_details(session: AsyncSession, flight_id: str) -> Optional[Flight]:
        """Fetch details for a specific flight."""
        result = await session.execute(select(Flight).where(Flight.id == flight_id))
        return result.scalars().first()

    @staticmethod
    async def get_flight_by_number(session: AsyncSession, flight_number: str) -> Optional[Flight]:
        """Look up a flight by its human-facing flight number (e.g. 'EK-601').

        A flight number is NOT unique — the same number recurs across dates — so
        this returns the earliest-departing matching flight as a representative
        record (all instances share airline, route, baggage, and duration).
        Returns None when nothing matches.
        """
        query = (
            select(Flight)
            .where(Flight.flight_number == flight_number.strip().upper())
            .order_by(Flight.departure_time)
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    def calculate_flight_price(flight: Flight, passenger_count: int) -> PriceBreakdown:
        """Calculate total price for a given number of passengers."""
        base_price = flight.base_price
        tax = (flight.tax_percent / 100) * base_price
        total_per_person = base_price + tax

        return PriceBreakdown(
            flight_id=flight.id,
            flight_number=flight.flight_number,
            passenger_count=passenger_count,
            base_price_per_person=base_price,
            tax_per_person=tax,
            total_per_person=total_per_person,
            grand_total=total_per_person * passenger_count,
            currency="USD"
        )

    @staticmethod
    async def filter_flights(
        session: AsyncSession,
        origin: str,
        destination: str,
        date: datetime,
        cabin_class: Optional[CabinClass] = None,
        max_stops: Optional[int] = None,
        airline: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        time_of_day: Optional[str] = None,  # "morning", "afternoon", "evening", "night"
    ) -> List[Flight]:
        """Filter flights with advanced criteria."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)

        filters = [
            Flight.origin == origin.upper(),
            Flight.destination == destination.upper(),
            Flight.departure_time >= start,
            Flight.departure_time <= end,
            Flight.is_active == True,
            Flight.status == FlightStatus.SCHEDULED
        ]

        if cabin_class:
            filters.append(Flight.cabin_class == cabin_class)
        if max_stops is not None:
            filters.append(Flight.stops <= max_stops)
        if airline:
            filters.append(Flight.airline == airline)
        if min_price is not None:
            filters.append(Flight.base_price >= min_price)
        if max_price is not None:
            filters.append(Flight.base_price <= max_price)

        if time_of_day:
            if time_of_day == "morning":
                filters.append(and_(Flight.departure_time >= start.replace(hour=6), Flight.departure_time < start.replace(hour=12)))
            elif time_of_day == "afternoon":
                filters.append(and_(Flight.departure_time >= start.replace(hour=12), Flight.departure_time < start.replace(hour=18)))
            elif time_of_day == "evening":
                filters.append(and_(Flight.departure_time >= start.replace(hour=18), Flight.departure_time <= end))
            elif time_of_day == "night":
                filters.append(or_(Flight.departure_time < start.replace(hour=6), Flight.departure_time > end))

        query = select(Flight).where(and_(*filters))
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def compare_flights(flights: List[Flight]) -> List[dict]:
        """Compare multiple flights and return a summary."""
        comparison = []
        for f in flights:
            comparison.append({
                "flight_id": f.id,
                "flight_number": f.flight_number,
                "airline": f.airline,
                "price": f.base_price * (1 + f.tax_percent / 100),
                "duration": f.duration_minutes,
                "stops": f.stops,
                "departure": f.departure_time
            })
        # Sort by price then duration
        comparison.sort(key=lambda x: (x["price"], x["duration"]))
        return comparison

    @staticmethod
    def check_seat_availability(flight: Flight, requested_seats: int) -> bool:
        """Check if enough seats are available."""
        return flight.available_seats >= requested_seats
