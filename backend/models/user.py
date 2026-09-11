"""
User SQLAlchemy ORM model.
Authentication-ready structure (password_hash placeholder for Phase 2).
"""
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship

from database.database import Base


class MembershipTier(str, enum.Enum):
    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=True)   # populated when auth is added

    membership = Column(SAEnum(MembershipTier), nullable=False, default=MembershipTier.STANDARD)
    loyalty_points = Column(String(20), nullable=False, default="0")   # stored as string to avoid float precision

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = relationship("Booking", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.membership}]>"
