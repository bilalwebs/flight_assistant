"""
Phase 8 — Travel Assistant Agent (specialist, reached via handoff from Triage).

A lightweight, general travel assistant for questions that are NOT flight
searches or specific-flight lookups, e.g.:
  * "What should I consider when choosing a flight?"
  * "What information do I need before booking?"
  * "What's the difference between a direct and a connecting flight?"
  * "What does baggage allowance mean?"

Intentionally simple: no tools, no database access, no external/real-time APIs,
no booking. It answers with GENERAL guidance only and must clearly distinguish
general explanations from actual flight facts (which only the search/details
specialists can provide from real data).
"""
from agents import Agent, RunContextWrapper

from config.model_config import DEFAULT_MODEL
from models.context import FlightAssistantContext


def _instructions(ctx: RunContextWrapper[FlightAssistantContext], agent: Agent) -> str:
    context = ctx.context
    name_note = (f" You are speaking with {context.user_name}."
                 if context and context.user_name else "")

    return f"""
You are a friendly, knowledgeable Travel Assistant for a Pakistan-based travel
platform.{name_note}

You answer GENERAL travel questions: explanations of flight terminology, how to
choose a flight, what to prepare before booking, baggage concepts, the meaning
of direct vs connecting vs non-stop flights, and similar guidance.

STRICT LIMITS:
- You have NO access to the flight database and NO tools. You must NOT state that
  any specific flight, price, schedule, seat, or availability exists. Speak only
  in general terms.
- If the user asks you to search for or find specific flights, or for the details
  of a specific flight, explain that this is general guidance and that a flight
  search or a specific-flight lookup is handled by the relevant specialist — then
  offer the general guidance you can give.
- Clearly separate GENERAL guidance from ACTUAL flight facts. Never present
  general knowledge as data about a real, bookable flight.
- Do NOT invent real-time information (delays, live prices, weather, visa rules).
- You do NOT handle booking or payment.

Keep answers clear, concise, and genuinely helpful.
""".strip()


travel_assistant_agent = Agent[FlightAssistantContext](
    name="Travel Assistant Agent",
    instructions=_instructions,
    model=DEFAULT_MODEL,
    handoff_description=(
        "Answers GENERAL travel questions that do NOT need live flight data: "
        "flight terminology, direct vs connecting flights, baggage concepts, how "
        "to choose a flight, and what to prepare before booking. Use for advice "
        "and explanations — NOT for searching flights or looking up a specific "
        "flight's details."
    ),
)
