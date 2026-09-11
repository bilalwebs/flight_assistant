"""
Pydantic schemas for API responses and agent structured outputs.
Kept separate from SQLAlchemy ORM models to maintain a clean boundary.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Flight schemas
# ──────────────────────────────────────────────────────────────

class FlightSchema(BaseModel):
    id: str
    flight_number: str
    airline: str
    airline_code: str
    origin: str
    destination: str
    origin_city: str
    destination_city: str
    origin_country: str
    destination_country: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    stop_airports: Optional[str] = None
    cabin_class: str
    base_price: float
    tax_percent: float
    total_price: float
    carry_on_kg: int
    checked_baggage_kg: int
    available_seats: int
    aircraft_type: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class FlightSearchResult(BaseModel):
    """Returned by the flight search tool — used by agents as structured output."""
    flights: List[FlightSchema]
    total_found: int
    origin: str
    destination: str
    search_date: Optional[str] = None
    message: str = ""


class FlightRecommendation(BaseModel):
    """AI-generated flight recommendation with reasoning."""
    recommended_flight_id: str
    flight_number: str
    reason: str
    price_usd: float
    duration_minutes: int
    stops: int


# ──────────────────────────────────────────────────────────────
# Agent structured-output contract (Phase 6)
# ──────────────────────────────────────────────────────────────

class FlightOption(BaseModel):
    """
    A single flight as presented in the Flight Search Agent's structured output.
    This is a lean, frontend/API-facing view — every field is populated ONLY
    from real flight-tool results, never invented.
    """
    flight_id: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str          # ISO-8601 string, copied from tool output
    arrival_time: str            # ISO-8601 string, copied from tool output
    duration_minutes: int
    stops: int
    cabin_class: str
    price: float                 # total price per person (base + tax), from tool output
    currency: str = "USD"
    baggage: str                 # e.g. "7kg carry-on, 23kg checked"


class FlightSearchResponse(BaseModel):
    """
    Validated structured output returned by the Flight Search Agent.

    Grounding contract:
      * Every flight in `flights` must come from an actual flight-tool result.
      * When no flights are found -> success=False, flights=[], nullable IDs.
      * When required info is missing -> needs_clarification=True, flights=[],
        `message` holds ONE clarifying question. The agent never fabricates.

    This model is pure data representation only; no business logic lives here.
    """
    success: bool
    message: str
    needs_clarification: bool = False
    flights: List[FlightOption] = []
    total_results: int = 0
    cheapest_flight_id: Optional[str] = None   # null when there are no results
    fastest_flight_id: Optional[str] = None    # null when there are no results


class FlightDetailsResponse(BaseModel):
    """
    Validated structured output returned by the Flight Details Agent (Phase 8).

    `flight` is null when the requested flight does not exist. Reuses FlightOption
    — the same lean, grounded flight view the search agent uses — instead of
    introducing a duplicate model. Pure data representation only; no business
    logic lives here.

    Grounding contract: `flight` is populated ONLY from a real flight-tool result
    (get_flight_details / find_flight_by_number). The agent never invents a flight.
    """
    success: bool
    message: str
    flight: Optional[FlightOption] = None



# ──────────────────────────────────────────────────────────────
# Booking schemas
# ──────────────────────────────────────────────────────────────

class PassengerInput(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    passenger_type: str = Field(default="adult")
    meal_preference: Optional[str] = None
    special_assistance: bool = False


class BookingCreateInput(BaseModel):
    flight_id: str
    user_id: str
    cabin_class: str = "economy"
    passengers: List[PassengerInput] = Field(..., min_length=1)
    contact_email: str
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class PassengerSchema(BaseModel):
    id: str
    first_name: str
    last_name: str
    passenger_type: str
    seat_number: Optional[str] = None
    meal_preference: Optional[str] = None

    model_config = {"from_attributes": True}


class BookingSchema(BaseModel):
    id: str
    pnr: str
    flight_id: str
    user_id: str
    cabin_class: str
    status: str
    passenger_count: int
    base_amount: float
    tax_amount: float
    total_amount: float
    currency: str
    contact_email: str
    contact_phone: Optional[str] = None
    passengers: List[PassengerSchema] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingResponse(BaseModel):
    """Returned by create_booking — used by AI agent structured outputs."""
    success: bool
    pnr: str
    booking_id: str
    status: str
    total_amount: float
    currency: str
    message: str


# ──────────────────────────────────────────────────────────────
# Payment schemas
# ──────────────────────────────────────────────────────────────

class PaymentInput(BaseModel):
    booking_id: str
    method: str = "simulated"
    card_last_four: Optional[str] = Field(None, pattern=r"^\d{4}$")


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    booking_id: str
    pnr: str
    amount: float
    currency: str
    status: str
    message: str


# ──────────────────────────────────────────────────────────────
# Price schemas
# ──────────────────────────────────────────────────────────────

class PriceBreakdown(BaseModel):
    """AI structured output for price calculation tool."""
    flight_id: str
    flight_number: str
    passenger_count: int
    base_price_per_person: float
    tax_per_person: float
    total_per_person: float
    grand_total: float
    currency: str = "USD"


# ──────────────────────────────────────────────────────────────
# Travel plan schema (orchestrator / planner agent output)
# ──────────────────────────────────────────────────────────────

class TravelPlan(BaseModel):
    """High-level travel plan generated by the travel planner agent."""
    origin: str
    destination: str
    travel_date: str
    recommended_flight: Optional[FlightRecommendation] = None
    estimated_total: Optional[float] = None
    tips: List[str] = []
    summary: str


# ──────────────────────────────────────────────────────────────
# Generic API response wrapper
# ──────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: str = ""
    error: Optional[str] = None
