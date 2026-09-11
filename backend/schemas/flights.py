"""
Phase 14 — Flight API Schemas.

Pydantic models for flight API requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class FlightSearchRequest(BaseModel):
    """Flight search request."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code (e.g., KHI)")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code (e.g., DXB)")
    date: datetime = Field(..., description="Departure date (ISO format)")
    cabin_class: Optional[str] = Field("economy", description="Cabin class: economy|business|first")

    model_config = {
        "json_schema_extra": {
            "example": {
                "origin": "KHI",
                "destination": "DXB",
                "date": "2026-09-07T00:00:00Z",
                "cabin_class": "economy"
            }
        }
    }


class FlightFilterRequest(BaseModel):
    """Advanced flight filter request."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code")
    date: datetime = Field(..., description="Departure date (ISO format)")
    cabin_class: Optional[str] = Field(None, description="Cabin class: economy|business|first")
    max_stops: Optional[int] = Field(None, ge=0, description="Maximum number of stops")
    airline: Optional[str] = Field(None, description="Airline code (e.g., EK)")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    time_of_day: Optional[str] = Field(None, description="Time of day: morning|afternoon|evening|night")

    model_config = {
        "json_schema_extra": {
            "example": {
                "origin": "KHI",
                "destination": "DXB",
                "date": "2026-09-07T00:00:00Z",
                "cabin_class": "economy",
                "max_stops": 0,
                "airline": "EK",
                "min_price": 100,
                "max_price": 500,
                "time_of_day": "morning"
            }
        }
    }


class FlightResponse(BaseModel):
    """Flight details response."""
    id: str = Field(..., description="Flight ID (UUID)")
    flight_number: str = Field(..., description="Flight number (e.g., EK-601)")
    airline: str = Field(..., description="Airline name")
    airline_code: str = Field(..., description="Airline code (e.g., EK)")
    origin: str = Field(..., description="Origin IATA code")
    destination: str = Field(..., description="Destination IATA code")
    origin_city: str = Field(..., description="Origin city name")
    destination_city: str = Field(..., description="Destination city name")
    departure_time: str = Field(..., description="Departure time (ISO format)")
    arrival_time: str = Field(..., description="Arrival time (ISO format)")
    duration_minutes: int = Field(..., description="Flight duration in minutes")
    stops: int = Field(..., description="Number of stops")
    cabin_class: str = Field(..., description="Cabin class: economy|business|first")
    base_price: float = Field(..., ge=0, description="Base price per passenger")
    tax_percent: float = Field(..., ge=0, description="Tax percentage")
    available_seats: int = Field(..., ge=0, description="Available seat count")
    total_seats: int = Field(..., gt=0, description="Total seat count")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "flight_number": "EK-601",
                "airline": "Emirates",
                "airline_code": "EK",
                "origin": "KHI",
                "destination": "DXB",
                "origin_city": "Karachi",
                "destination_city": "Dubai",
                "departure_time": "2026-09-07T10:00:00Z",
                "arrival_time": "2026-09-07T12:30:00Z",
                "duration_minutes": 150,
                "stops": 0,
                "cabin_class": "economy",
                "base_price": 150.0,
                "tax_percent": 15.0,
                "available_seats": 45,
                "total_seats": 180
            }
        }
    }


class PriceBreakdownResponse(BaseModel):
    """Price calculation response."""
    flight_id: str = Field(..., description="Flight ID")
    flight_number: str = Field(..., description="Flight number")
    passenger_count: int = Field(..., description="Number of passengers")
    base_price_per_person: float = Field(..., description="Base price per passenger")
    tax_per_person: float = Field(..., description="Tax per passenger")
    total_per_person: float = Field(..., description="Total per passenger")
    grand_total: float = Field(..., description="Grand total for all passengers")
    currency: str = Field(..., description="Currency code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "flight_id": "550e8400-e29b-41d4-a716-446655440000",
                "flight_number": "EK-601",
                "passenger_count": 2,
                "base_price_per_person": 150.0,
                "tax_per_person": 22.5,
                "total_per_person": 172.5,
                "grand_total": 345.0,
                "currency": "USD"
            }
        }
    }


class SeatAvailabilityResponse(BaseModel):
    """Seat availability response."""
    flight_id: str = Field(..., description="Flight ID")
    flight_number: str = Field(..., description="Flight number")
    available_seats: int = Field(..., ge=0, description="Number of available seats")
    total_seats: int = Field(..., gt=0, description="Total number of seats")

    model_config = {
        "json_schema_extra": {
            "example": {
                "flight_id": "550e8400-e29b-41d4-a716-446655440000",
                "flight_number": "EK-601",
                "available_seats": 45,
                "total_seats": 180
            }
        }
    }
