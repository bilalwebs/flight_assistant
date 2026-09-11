"""Phase 5–9 agent package exports.

Two independent multi-agent entry points coexist:
  * `flight_triage_agent`       — Phase 8, HANDOFF routing (control transfers).
  * `flight_orchestrator_agent` — Phase 9, AGENTS-AS-TOOLS (control retained).
Both reuse the same three specialists and the same shared FlightAssistantContext.
"""
from .flight_search_agent import flight_search_agent
from .flight_details_agent import flight_details_agent
from .travel_assistant_agent import travel_assistant_agent
from .flight_triage_agent import flight_triage_agent
from .flight_orchestrator_agent import (
    flight_orchestrator_agent,
    ORCHESTRATOR_TOOLS,
)

__all__ = [
    "flight_search_agent",
    "flight_details_agent",
    "travel_assistant_agent",
    "flight_triage_agent",
    "flight_orchestrator_agent",
    "ORCHESTRATOR_TOOLS",
]
