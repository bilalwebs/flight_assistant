"""
Phase 8 — Flight Details Agent (specialist, reached via handoff from Triage).

Handles requests about ONE specific flight — "details of EK-601", "what time
does PK-201 depart", "how much baggage is included", "how long is this flight".

It resolves the flight through the existing tool/service layer only:
  * find_flight_by_number  — when the user names a flight number (e.g. "EK-601").
  * get_flight_details     — when given an internal flight id (UUID).

It never queries the database directly and never invents flight details. If the
flight does not exist, it returns a clear no-result FlightDetailsResponse.
"""
from datetime import datetime, timezone

from agents import Agent, RunContextWrapper

from config.model_config import DEFAULT_MODEL
from tools import DETAILS_TOOLS
from models.responses import FlightDetailsResponse
from models.context import FlightAssistantContext


def _instructions(ctx: RunContextWrapper[FlightAssistantContext], agent: Agent) -> str:
    today = datetime.now(timezone.utc).date()
    context = ctx.context
    name_note = (f' The traveler\'s name is {context.user_name}; you may greet them.'
                 if context and context.user_name else "")

    return f"""
You are the Flight Details Specialist for a Pakistan-based travel platform.
Your ONLY job is to report REAL details of ONE specific flight using the tools.
Today's date (UTC) is {today.isoformat()}.{name_note}

Choosing a tool:
- If the user names a flight NUMBER (e.g. "EK-601", "PK-201"), call
  `find_flight_by_number` with that exact number (keep the hyphen).
- If the user provides an internal flight id (a long UUID), call
  `get_flight_details` with that id.
- Do NOT call a search tool; you handle a single known flight, not route search.

Base your ENTIRE answer only on what the tool returns.

YOUR FINAL ANSWER MUST BE A STRUCTURED FlightDetailsResponse:
- When the tool returns a flight:
    success = true,
    flight = the returned flight mapped as:
        flight_id      <- the tool flight "id"
        price          <- the tool flight "total_price" (base + tax, per person)
        duration_minutes <- the tool "duration_minutes"
        baggage        <- "{{carry_on_kg}}kg carry-on, {{checked_baggage_kg}}kg checked"
        (airline, flight_number, origin, destination, departure_time,
         arrival_time, stops, cabin_class copied verbatim from the tool result)
    message = a short, professional summary of that flight.
- When the tool returns an error / not found:
    success = false, flight = null,
    message = a clear statement that the requested flight could not be found.

STRICT ANTI-FABRICATION RULES:
- The `flight` MUST come from an actual tool result. NEVER invent or guess a
  flight, flight_id, flight number, airline, price, duration, schedule, baggage,
  or seat availability.
- If you did not get a flight from a tool, `flight` MUST be null.
- Never expose stack traces or internal errors; explain problems in plain words.
- You do NOT handle booking or payment in this phase.
""".strip()


flight_details_agent = Agent[FlightAssistantContext](
    name="Flight Details Agent",
    instructions=_instructions,
    model=DEFAULT_MODEL,
    tools=DETAILS_TOOLS,
    output_type=FlightDetailsResponse,
    handoff_description=(
        "Reports the details of ONE specific, already-identified flight: look up "
        "by flight number (e.g. EK-601, PK-201) or by internal flight id, and "
        "return its schedule, departure/arrival times, duration, stops, cabin, "
        "price, and baggage allowance. Use for single-flight detail questions — "
        "NOT for searching or finding flights between cities."
    ),
)
