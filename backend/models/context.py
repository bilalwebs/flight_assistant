"""
Phase 7 — Agent Context model.

`FlightAssistantContext` carries per-request USER / PREFERENCE information into
the Flight Search Agent through the Agents SDK Runner:

    Runner.run(starting_agent=flight_search_agent, input=..., context=ctx)

The SDK then exposes this object to the agent's tools and dynamic-instruction
function via `RunContextWrapper.context`. Nothing here is global or mutable
shared state — a fresh context is passed per request.

STRICT BOUNDARIES (important):
  * This is CONTEXT — who is asking and what they generally prefer. It is NOT a
    source of flight facts.
  * Preferences may influence HOW the agent searches or what it recommends, but
    a preference must NEVER be presented as an available flight, price, airline,
    cabin, schedule, or seat. Every real flight fact must still come from a tool
    result (FlightService → database).
  * No business logic lives in this model. It is a plain, typed data container,
    intentionally easy to extend for later booking/session phases.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FlightAssistantContext:
    """Per-request traveler profile / preferences supplied by the application.

    Every field is optional (with sensible defaults) so the agent runs correctly
    even when no context — or only a partial context — is provided.
    """

    user_id: Optional[str] = None
    user_name: Optional[str] = None

    # Contact details supplied by the authenticated user (Phase 14). Used for
    # personalisation and booking contact defaults — never as flight facts.
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

    # API-supplied travel preferences. `cabin_preference` mirrors
    # `preferred_cabin_class`; the API sets both so agent instructions
    # (which read `preferred_cabin_class`) stay untouched.
    origin_preference: Optional[str] = None
    destination_preference: Optional[str] = None
    cabin_preference: Optional[str] = None

    # Preference for the cabin to search when the user does NOT specify one.
    # Expected values mirror CabinClass: "economy" | "premium_economy" |
    # "business" | "first". Kept as a plain string to keep this model free of
    # ORM/enum coupling; the agent maps it when calling tools.
    preferred_cabin_class: Optional[str] = None

    # Display currency preference. Phase 7 does NOT convert currencies, so this
    # only affects wording — actual prices remain the database currency (USD).
    preferred_currency: str = "USD"

    # Preferred airline to surface when the user does NOT name one.
    preferred_airline: Optional[str] = None

    # Free-form trip descriptor, e.g. "one_way" | "round_trip" | "business" |
    # "leisure". Used only to personalise messaging, never as a flight fact.
    trip_type: Optional[str] = None
