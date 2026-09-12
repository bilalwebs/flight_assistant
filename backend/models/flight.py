"""
Flight SQLAlchemy ORM model.
Designed so a real flight-API service can replace seed data without schema changes.
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Enum as SAEnum,
    Boolean, Text, CheckConstraint,
)
from sqlalchemy.orm import relationship

from database.database import Base
from utils.datetime_utils import utcnow


class CabinClass(str, enum.Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class FlightStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Flight(Base):
    __tablename__ = "flights"

    id = Column(String(36), primary_key=True)           # UUID string
    flight_number = Column(String(10), nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    airline_code = Column(String(3), nullable=False)    # IATA code e.g. PK, EK

    # Route
    origin = Column(String(3), nullable=False, index=True)       # IATA airport
    destination = Column(String(3), nullable=False, index=True)
    origin_city = Column(String(100), nullable=False)
    destination_city = Column(String(100), nullable=False)
    origin_country = Column(String(100), nullable=False)
    destination_country = Column(String(100), nullable=False)

    # Times
    # Schedule instants are persisted as naive UTC (consistent with seed data,
    # tools, agents and search comparisons) — TIMESTAMP WITHOUT TIME ZONE on PG.
    departure_time = Column(DateTime, nullable=False, index=True)
    arrival_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    # Route details
    stops = Column(Integer, nullable=False, default=0)
    stop_airports = Column(Text, nullable=True)         # JSON list of IATA codes

    # Cabin / pricing
    cabin_class = Column(SAEnum(CabinClass), nullable=False, default=CabinClass.ECONOMY)
    base_price = Column(Float, nullable=False)
    tax_percent = Column(Float, nullable=False, default=15.0)

    # Baggage
    carry_on_kg = Column(Integer, nullable=False, default=7)
    checked_baggage_kg = Column(Integer, nullable=False, default=23)

    # Availability
    total_seats = Column(Integer, nullable=False, default=180)
    available_seats = Column(Integer, nullable=False)

    # Meta
    aircraft_type = Column(String(50), nullable=True)
    status = Column(SAEnum(FlightStatus), nullable=False, default=FlightStatus.SCHEDULED)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    bookings = relationship("Booking", back_populates="flight", lazy="selectin")

    __table_args__ = (
        CheckConstraint("available_seats >= 0", name="ck_flight_seats_nonneg"),
        CheckConstraint("base_price > 0", name="ck_flight_price_positive"),
        CheckConstraint("stops >= 0", name="ck_flight_stops_nonneg"),
    )

    @property
    def total_price(self) -> float:
        return round(self.base_price * (1 + self.tax_percent / 100), 2)

    def __repr__(self) -> str:
        return f"<Flight {self.flight_number} {self.origin}→{self.destination}>"
