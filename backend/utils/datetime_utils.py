"""
Timezone-safe datetime helpers.

Project standard: application-generated timestamps are timezone-aware UTC
datetimes. Use `utcnow()` instead of the deprecated `datetime.utcnow()` so
SQLAlchemy columns declared with `DateTime(timezone=True)` never receive a
naive value.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)