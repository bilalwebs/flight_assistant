"""
Phase 10 — Guarded Flight Tools.

Attaches tool input guardrails to all flight tools WITHOUT modifying the
original unguarded tools from tools.flight_tools.

How this works:
  * `validate_flight_tool_inputs` is ALREADY a ToolInputGuardrail instance
    produced by the @tool_input_guardrail decorator — we attach it directly
    and never wrap it a second time.
  * The Agents SDK provides FunctionTool.__copy__ specifically so tools can be
    duplicated into new instances. This module uses that copy to give every
    guarded tool its OWN guardrail list, so guardrails never leak onto the
    shared unguarded tools (which the REST/lower layers keep using unchanged).

Tool names, JSON schemas, description and execution behavior are preserved
because each guarded tool is a copy of the original with only the
`tool_input_guardrails` field overridden.
"""
import copy

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


def _guard_tool(tool):
    """Return a guarded copy of *tool*, leaving the original untouched."""
    guarded_tool = copy.copy(tool)
    guarded_tool.tool_input_guardrails = [validate_flight_tool_inputs]
    return guarded_tool


GUARDED_FLIGHT_TOOLS = [
    _guard_tool(tool)
    for tool in [
        search_flights,
        filter_flights,
        get_flight_details,
        find_flight_by_number,
        compare_flights,
        calculate_flight_price,
        check_seat_availability,
    ]
]

__all__ = [
    "GUARDED_FLIGHT_TOOLS",
]
