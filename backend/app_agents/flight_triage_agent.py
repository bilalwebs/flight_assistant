"""
Phase 8 — Flight Triage Agent (main entry point, multi-agent router).

Architecture:
    User
     -> Flight Triage Agent            (this file — routing ONLY)
        ├── handoff -> Flight Search Agent      (search / find / filter / compare)
        ├── handoff -> Flight Details Agent     (one specific flight's details)
        └── handoff -> Travel Assistant Agent   (general travel guidance)

The Triage Agent's sole responsibility is to understand intent and ROUTE to the
correct specialist via the Agents SDK `handoffs` mechanism. It performs no flight
work itself, calls no flight tools, and never invents flight information. After a
handoff the specialist produces the final (structured) output.

The shared `FlightAssistantContext` flows through the Runner and, because the SDK
shares run-level context across the handoff chain, every specialist sees the same
`ctx.context` — no manual copying, no globals.
"""
from agents import Agent, RunContextWrapper, ModelSettings

from config.model_config import DEFAULT_MODEL
from models.context import FlightAssistantContext

from .flight_search_agent import flight_search_agent
from .flight_details_agent import flight_details_agent
from .travel_assistant_agent import travel_assistant_agent


def _instructions(ctx: RunContextWrapper[FlightAssistantContext], agent: Agent) -> str:
    context = ctx.context
    who = (f" You are assisting {context.user_name}."
           if context and context.user_name else "")

    return f"""
You are the Flight Triage Agent — the single entry point of a Pakistan-based
travel assistant.{who}

Your ONLY job is to ROUTE the user's request to the correct specialist by handing
off. You do NOT answer flight questions yourself, you do NOT call flight tools,
and you NEVER invent flights, prices, schedules, airlines, or availability.

Route as follows — always hand off to exactly one specialist:

- Flight Search Agent — when the user wants to SEARCH or FIND flights: a route
  between cities, by date, price limit, airline, non-stop/stops, cabin class, or
  comparing available options. ALSO route here when the user clearly wants a
  flight but has NOT given enough detail (e.g. "I need a flight") — that agent
  asks the clarifying question.

- Flight Details Agent — when the user asks about ONE specific, already-identified
  flight: a flight number (e.g. "EK-601", "PK-201") or a flight id — its schedule,
  departure/arrival, duration, stops, cabin, price, or baggage.

- Travel Assistant Agent — for GENERAL travel questions that do not need live
  flight data: terminology, direct vs connecting flights, baggage concepts, how
  to choose a flight, or what to prepare before booking.

Always transfer to the specialist that best matches the intent. Do not produce
the final answer yourself.
""".strip()


flight_triage_agent = Agent[FlightAssistantContext](
    name="Flight Triage Agent",
    instructions=_instructions,
    model=DEFAULT_MODEL,
    handoffs=[flight_search_agent, flight_details_agent, travel_assistant_agent],
    # Force the triage turn to select a handoff (its only tools are the handoff
    # transfers) so routing is deterministic — it can never answer on its own.
    model_settings=ModelSettings(tool_choice="required"),
)
