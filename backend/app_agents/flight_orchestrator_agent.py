"""
Phase 9 — Flight Orchestrator Agent (AGENTS-AS-TOOLS entry point).

╔══════════════════════════════════════════════════════════════════════════════╗
║ PHASE 8 (handoff) vs PHASE 9 (agent-as-tool) — the essential distinction     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Phase 8 — HANDOFF (`flight_triage_agent.py`, still fully intact):

    Triage Agent
        │  handoff (transfer_to_*)
        ▼
    Specialist Agent  ──►  produces the FINAL output

  Control TRANSFERS. The specialist becomes the active agent and owns the final
  answer, so `result.last_agent` is the SPECIALIST and the run's final output type
  is the specialist's own `output_type`. The triage agent is done talking.

Phase 9 — AGENT AS TOOL (this file):

    Orchestrator Agent
        │  tool call (search_flights_agent / get_flight_details_agent / ...)
        ▼
    Specialist Agent  ──►  returns a tool RESULT
        │
        ▼
    Orchestrator Agent  ──►  produces the FINAL output

  Control is RETAINED. Each specialist runs as a nested `Runner.run` and returns
  its result back to the orchestrator as a tool output. `result.last_agent` stays
  the ORCHESTRATOR, which can call MULTIPLE specialists in one turn and compose
  their results into one answer — impossible with a handoff, which is one-way.

Architecture:
    User
     -> Flight Orchestrator Agent            (this file — orchestration ONLY)
        ├── tool: search_flights_agent       -> Flight Search Agent
        ├── tool: get_flight_details_agent   -> Flight Details Agent
        └── tool: travel_assistant_agent     -> Travel Assistant Agent

The orchestrator performs NO flight work of its own: it never touches the
database, never calls FlightService, never computes prices, and never invents
flight facts. All flight truth comes from a specialist's tool result.

CONTEXT PROPAGATION (no globals, no second context object):
`Agent.as_tool()` invokes the specialist via a nested `Runner.run(...,
context=nested_context)` where `nested_context.context` is the *same*
`FlightAssistantContext` instance the parent run holds. So the chain

    Runner -> Orchestrator -> agent-as-tool -> Specialist -> specialist tools

all observe one shared `ctx.context`. Preferences set once are visible to the
specialist's dynamic instructions and tools automatically.

STRUCTURED OUTPUT ACROSS THE TOOL BOUNDARY:
A specialist's `output_type` governs its OWN run, so the nested run still yields a
validated `FlightSearchResponse` / `FlightDetailsResponse`. Because a tool result
must be a string for the model, we attach a `custom_output_extractor` that
serialises the validated model to canonical JSON (`model_dump_json`). That keeps
flight ids, prices, totals and cheapest/fastest ids EXACT — the orchestrator reads
real data rather than a re-worded summary, which is what makes the
"no fabricated transformation" rule enforceable.
"""
from typing import Union

from agents import Agent, RunContextWrapper, RunResult, RunResultStreaming

from config.model_config import DEFAULT_MODEL
from models.context import FlightAssistantContext
from models.responses import FlightSearchResponse, FlightDetailsResponse

from .flight_search_agent import flight_search_agent
from .flight_details_agent import flight_details_agent
from .travel_assistant_agent import travel_assistant_agent


# ──────────────────────────────────────────────────────────────────────────────
# Output extraction — preserve the specialist's structured result EXACTLY.
# ──────────────────────────────────────────────────────────────────────────────

async def _extract_structured_output(
    run_result: Union[RunResult, RunResultStreaming],
) -> str:
    """Serialise a specialist's validated structured output to canonical JSON.

    Without this, a Pydantic final output would be coerced to a string by the SDK
    with no guarantee about shape. Emitting `model_dump_json()` means the
    orchestrator receives the specialist's REAL field values (flight_id, price,
    total_results, cheapest/fastest ids) verbatim, so it can report them without
    guessing or recomputing. Text-only specialists pass straight through.
    """
    output = run_result.final_output
    if isinstance(output, (FlightSearchResponse, FlightDetailsResponse)):
        return output.model_dump_json()
    return output if isinstance(output, str) else str(output)


# ──────────────────────────────────────────────────────────────────────────────
# Specialist agents exposed as TOOLS via the SDK's `Agent.as_tool()` mechanism.
# ──────────────────────────────────────────────────────────────────────────────

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

ORCHESTRATOR_TOOLS = [
    search_flights_agent_tool,
    get_flight_details_agent_tool,
    travel_assistant_agent_tool,
]


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator instructions (context-aware, orchestration-only)
# ──────────────────────────────────────────────────────────────────────────────

def _instructions(ctx: RunContextWrapper[FlightAssistantContext], agent: Agent) -> str:
    context = ctx.context
    who = (f" You are assisting {context.user_name}."
           if context and context.user_name else "")

    return f"""
You are the Flight Orchestrator for a Pakistan-based travel assistant.{who}

You coordinate three SPECIALIST AGENTS that you call as TOOLS. You keep control of
the conversation: you call a specialist, read its result, and then write the final
answer yourself.

YOUR TOOLS:
- `search_flights_agent` — searching / finding / filtering / comparing flights.
  Returns a FlightSearchResponse as JSON.
- `get_flight_details_agent` — details of ONE specific flight identified by a
  flight number (e.g. "EK-601") or a flight id. Returns a FlightDetailsResponse
  as JSON.
- `travel_assistant_agent` — general travel questions needing no live data
  (terminology, direct vs connecting, what baggage allowance means, how to
  choose a flight). Returns plain text.

HOW TO WORK:
1. Read the request and decide which specialist(s) it needs.
2. Call the RIGHT specialist tool, forwarding the user's request in full natural
   language — include every detail they gave (cities, date, cabin class, airline,
   budget, flight number). Never drop or alter a detail.
3. If the request genuinely has SEVERAL parts needing DIFFERENT specialists (e.g.
   "find me a flight ... and also explain what baggage allowance means"), call
   each relevant specialist and combine their results in your answer.
4. Call only the specialists you actually need. One specialist is usually enough —
   do not call extra tools for a single-purpose request.

STRICT RULES — you ORCHESTRATE, you do not do the work:
- You have NO database access and NO flight tools of your own. You must NOT
  search flights, look up flights, or compute prices yourself.
- EVERY flight fact you state (flight id, flight number, airline, price, times,
  duration, stops, cabin, baggage, availability, totals) MUST come from a
  specialist's tool result. NEVER invent, guess, adjust, round, recalculate or
  "improve" any value. Report the specialist's numbers exactly as returned.
- Do NOT duplicate or second-guess specialist logic. If the search specialist
  returns no flights, say there are no flights — never substitute a flight of
  your own, and never present a preference as if it were an available flight.
- If a specialist reports no results, an error, or asks a clarifying question,
  relay that faithfully and helpfully. Do not fabricate a fallback flight.
- Never expose stack traces or internal errors; explain problems in plain words.
- You do NOT handle booking or payment in this phase.

USER PREFERENCES vs FACTS:
Preferences in context (cabin, airline, currency) may guide what you ask a
specialist for, but they are NOT flight facts. An EXPLICIT request from the user
in this message ALWAYS overrides a stored preference — if the user asks for
economy while the profile prefers business, forward ECONOMY; if the user asks for
PIA while the profile prefers Emirates, forward PIA.

Prices are in USD, the database currency. Do NOT convert currencies or invent
exchange rates.

Answer clearly, concisely and professionally, grounded only in specialist results.
""".strip()


flight_orchestrator_agent = Agent[FlightAssistantContext](
    name="Flight Orchestrator Agent",
    instructions=_instructions,
    model=DEFAULT_MODEL,
    tools=ORCHESTRATOR_TOOLS,
    # NOTE: deliberately no `output_type`. The orchestrator composes a natural
    # language answer from one or more specialist results (which may have
    # DIFFERENT structured types), so a single output schema would not fit.
    # Structured data is preserved inside each agent-tool result as exact JSON.
)
