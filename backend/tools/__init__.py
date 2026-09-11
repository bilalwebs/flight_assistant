"""
Agent-facing tool layer.

Exposes the flight function-tools as ready-to-use lists so Agents can be
constructed with the tools they need.

  * FLIGHT_TOOLS  — the full search/compare/price toolset (Flight Search Agent).
  * DETAILS_TOOLS — single-flight lookup tools (Flight Details Agent).
"""
from .flight_tools import (
    search_flights,
    get_flight_details,
    find_flight_by_number,
    filter_flights,
    compare_flights,
    calculate_flight_price,
    check_seat_availability,
)

FLIGHT_TOOLS = [
    search_flights,
    get_flight_details,
    filter_flights,
    compare_flights,
    calculate_flight_price,
    check_seat_availability,
]

# Tools used by the Flight Details Agent to resolve ONE specific flight,
# either by its internal id or by its human-facing flight number.
DETAILS_TOOLS = [
    find_flight_by_number,
    get_flight_details,
]

__all__ = [
    "FLIGHT_TOOLS",
    "DETAILS_TOOLS",
    "search_flights",
    "get_flight_details",
    "find_flight_by_number",
    "filter_flights",
    "compare_flights",
    "calculate_flight_price",
    "check_seat_availability",
]
