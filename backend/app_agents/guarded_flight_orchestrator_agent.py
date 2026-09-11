"""
Phase 10 — Guarded Flight Orchestrator Agent.

This is the PRODUCTION-FACING orchestration entry point with full guardrails:
  * Input Guardrail: rejects clearly out-of-scope requests
  * Output Guardrail: validates structured output invariants
  * Tool Guardrails: attached to all flight tools (inherited by specialists)

Architecture remains identical to Phase 9's unguarded orchestrator, but with
safety layers added at input, tool, and output boundaries.

Note on tool guardrails: The specialist agents (Flight Search, Flight Details)
use their own tools internally. To apply guardrails to those tools, we need to
modify the specialists BEFORE wrapping them as agent-tools. We do this by
creating guardrail-aware copies of the specialists.
"""
from agents import Agent

from config.model_config import DEFAULT_MODEL
from models.context import FlightAssistantContext
from guardrails import scope_input_guardrail, validate_output_guardrail
from tools.guarded_flight_tools import GUARDED_FLIGHT_TOOLS

# Import the Phase 9 orchestrator's instructions and output extractor
from app_agents.flight_orchestrator_agent import (
    _instructions,
    _extract_structured_output,
    ORCHESTRATOR_TOOLS,
)

# Import the specialist agents
from app_agents.flight_search_agent import flight_search_agent as _flight_search_agent
from app_agents.flight_details_agent import flight_details_agent as _flight_details_agent
from app_agents.travel_assistant_agent import travel_assistant_agent as _travel_assistant_agent


# ──────────────────────────────────────────────────────────────────────────
# Create guarded specialist agents by cloning with guarded tools.
# ──────────────────────────────────────────────────────────────────────────

# The specialists need access to the GUARDED flight tools to benefit from
# tool input guardrails. We create new agent instances with the guarded tools.
# (We cannot mutate the originals because they are shared with Phase 8/9 unguarded paths.)

flight_search_agent = Agent[FlightAssistantContext](
    name="Flight Search Agent",
    instructions=_flight_search_agent.instructions,
    model=_flight_search_agent.model,
    tools=GUARDED_FLIGHT_TOOLS,  # Use guarded tools
    output_type=_flight_search_agent.output_type,
    handoff_description=_flight_search_agent.handoff_description,
)

flight_details_agent = Agent[FlightAssistantContext](
    name="Flight Details Agent",
    instructions=_flight_details_agent.instructions,
    model=_flight_details_agent.model,
    tools=[t for t in GUARDED_FLIGHT_TOOLS if t.name in ("find_flight_by_number", "get_flight_details")],
    output_type=_flight_details_agent.output_type,
    handoff_description=_flight_details_agent.handoff_description,
)

# Travel Assistant doesn't use flight tools, so no changes needed
travel_assistant_agent = _travel_assistant_agent


# ──────────────────────────────────────────────────────────────────────────
# Create guarded agent-tools for the orchestrator
# ──────────────────────────────────────────────────────────────────────────

search_flights_agent_tool = flight_search_agent.as_tool(
    tool_name="search_flights_agent",
    tool_description=(
        "Use to SEARCH or FIND flights. Delegates to the Flight Search Agent, "
        "which queries the real flight database and returns a structured "
        "FlightSearchResponse as JSON. Use for a route between cities, a date, a "
        "price limit, an airline, non-stop/stops, a cabin class, or comparing "
        "options — and also when the user clearly wants a flight but has not "
        "given enough detail (the specialist asks the clarifying question). "
        "Pass the user's flight-search request in full, in natural language, "
        "including every detail they gave (cities, date, cabin, airline, budget)."
    ),
    custom_output_extractor=_extract_structured_output,
)

get_flight_details_agent_tool = flight_details_agent.as_tool(
    tool_name="get_flight_details_agent",
    tool_description=(
        "Use for ONE specific, already-identified flight. Delegates to the Flight "
        "Details Agent, which looks the flight up by flight NUMBER (e.g. EK-601, "
        "PK-201) or internal flight id and returns a structured "
        "FlightDetailsResponse as JSON with its schedule, departure/arrival, "
        "duration, stops, cabin, price and baggage allowance. Do NOT use for "
        "searching flights between cities. Pass the flight number or id exactly "
        "as the user wrote it."
    ),
    custom_output_extractor=_extract_structured_output,
)

travel_assistant_agent_tool = travel_assistant_agent.as_tool(
    tool_name="travel_assistant_agent",
    tool_description=(
        "Use for GENERAL travel questions that need NO live flight data: flight "
        "terminology, direct vs connecting vs non-stop, what baggage allowance "
        "means, how to choose a flight, what to prepare before booking. "
        "Delegates to the Travel Assistant Agent and returns a plain-text "
        "explanation. Do NOT use to search flights or to look up a specific "
        "flight's details."
    ),
)

GUARDED_ORCHESTRATOR_TOOLS = [
    search_flights_agent_tool,
    get_flight_details_agent_tool,
    travel_assistant_agent_tool,
]


guarded_flight_orchestrator_agent = Agent[FlightAssistantContext](
    name="Guarded Flight Orchestrator Agent",
    instructions=_instructions,
    model=DEFAULT_MODEL,
    tools=GUARDED_ORCHESTRATOR_TOOLS,
    input_guardrails=[scope_input_guardrail],
    output_guardrails=[validate_output_guardrail],
)

