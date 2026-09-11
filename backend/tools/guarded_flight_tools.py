"""
Phase 10 — Guarded Flight Tools.

Wraps existing Phase 4 flight tools with input/output guardrails.

This layer does NOT modify the original tools; it creates new tool instances
with guardrails attached. The original unguarded tools remain available for
non-production or development use.

The guardrails validate arguments before tool execution and can short-circuit
obviously invalid calls (e.g., negative prices, origin==destination) before
they reach FlightService.
"""
from agents.tool_guardrails import ToolInputGuardrail

from guardrails.tool_guardrails import validate_flight_tool_inputs
from tools.flight_tools import (
    search_flights,
    filter_flights,
    get_flight_details,
    find_flight_by_number,
    compare_flights,
    calculate_flight_price,
    check_seat_availability,
)


# Attach the tool input guardrail to all flight tools.
# The guardrail will validate arguments before any tool is invoked.
# Note: FunctionTool.tool_input_guardrails expects a list, or None (default).

def add_guardrail_to_tool(tool, guardrail: ToolInputGuardrail):
    """Attach a tool input guardrail to an existing FunctionTool."""
    if tool.tool_input_guardrails is None:
        tool.tool_input_guardrails = []
    tool.tool_input_guardrails.append(guardrail)
    return tool


# Apply the guardrail to all flight tools.
guardrail = ToolInputGuardrail(
    guardrail_function=validate_flight_tool_inputs,
    name="flight_tool_validation",
)

for tool in [search_flights, filter_flights, get_flight_details, find_flight_by_number,
             compare_flights, calculate_flight_price, check_seat_availability]:
    add_guardrail_to_tool(tool, guardrail)


# Export the now-guarded tools for use in agents.
GUARDED_FLIGHT_TOOLS = [
    search_flights,
    filter_flights,
    get_flight_details,
    find_flight_by_number,
    compare_flights,
    calculate_flight_price,
    check_seat_availability,
]

__all__ = [
    "GUARDED_FLIGHT_TOOLS",
    "search_flights",
    "filter_flights",
    "get_flight_details",
    "find_flight_by_number",
    "compare_flights",
    "calculate_flight_price",
    "check_seat_availability",
]
