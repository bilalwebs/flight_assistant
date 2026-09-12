"""
Booking, Passenger, and Payment SQLAlchemy ORM models.
One booking contains 1-N passengers and exactly one payment record.
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    Enum as SAEnum, Boolean, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from database.database import Base
from utils.datetime_utils import utcnow


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    STRIPE = "stripe"
    SIMULATED = "simulated"


class PassengerType(str, enum.Enum):
    ADULT = "adult"
    CHILD = "child"
    INFANT = "infant"


# ──────────────────────────────────────────────────────────────
# Booking
# ──────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True)
    pnr = Column(String(10), nullable=False, unique=True, index=True)   # e.g. AB1234

    # FK references
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    flight_id = Column(String(36), ForeignKey("flights.id"), nullable=False, index=True)

    # Booking details
    cabin_class = Column(String(30), nullable=False, default="economy")
    status = Column(SAEnum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    passenger_count = Column(Integer, nullable=False, default=1)

    # Pricing snapshot (locked at booking time)
    base_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")

    # Contact
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)

    # Meta
    notes = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="bookings", lazy="selectin")
    flight = relationship("Flight", back_populates="bookings", lazy="selectin")
    passengers = relationship("Passenger", back_populates="booking", cascade="all, delete-orphan", lazy="selectin")
    payment = relationship("Payment", back_populates="booking", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Booking PNR={self.pnr} status={self.status}>"


# ──────────────────────────────────────────────────────────────
# Passenger
# ──────────────────────────────────────────────────────────────

class Passenger(Base):
    __tablename__ = "passengers"

    id = Column(String(36), primary_key=True)
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(String(10), nullable=False)       # YYYY-MM-DD string
    passport_number = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    passenger_type = Column(SAEnum(PassengerType), nullable=False, default=PassengerType.ADULT)

    seat_number = Column(String(5), nullable=True)          # e.g. 14A
    meal_preference = Column(String(50), nullable=True)     # e.g. vegetarian
    special_assistance = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="passengers")

    def __repr__(self) -> str:
        return f"<Passenger {self.first_name} {self.last_name} [{self.passenger_type}]>"


# ──────────────────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True)
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, unique=True, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    method = Column(SAEnum(PaymentMethod), nullable=False, default=PaymentMethod.SIMULATED)
    status = Column(SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)

    # Stripe identifiers
    stripe_checkout_session_id = Column(String(255), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    stripe_charge_id = Column(String(255), nullable=True, index=True)

    # Stripe metadata for webhook idempotency
    stripe_event_id = Column(String(255), nullable=True, index=True)

    # Card info — never store full card, only reference
    card_last_four = Column(String(4), nullable=True)

    # Gateway response (Stripe API response, sanitized)
    gateway_response = Column(Text, nullable=True)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment {self.stripe_charge_id or self.id} {self.status} ${self.amount}>"
