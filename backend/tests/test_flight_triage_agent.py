"""
Phase 8 — Handoffs + Multi-Agent Routing test suite.

Every scenario runs the REAL multi-agent system by starting at the Flight Triage
Agent via `Runner.run(starting_agent=flight_triage_agent, ...)`. We prove the
ACTUAL SDK handoff mechanism fired (not textual guessing) by inspecting:
  * result.new_items for `HandoffOutputItem`s (source_agent -> target_agent), and
  * result.last_agent — the specialist that produced the final output.

We also keep every earlier guarantee intact: structured outputs remain valid,
context survives the handoff, explicit requests still override preferences, and
no flight fact is ever fabricated (ids/prices are checked against the live DB).
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from openai import RateLimitError

from agents import Runner, set_tracing_disabled

from app_agents import flight_triage_agent
from models.responses import FlightSearchResponse, FlightDetailsResponse
from models.context import FlightAssistantContext
from models.flight import Flight, CabinClass
from services.flight_service import FlightService
from database.database import AsyncSessionLocal

set_tracing_disabled(True)

PASS, FAIL = "PASS", "FAIL"
TOMORROW = datetime.now(timezone.utc).date() + timedelta(days=1)
TOMORROW_DT = datetime(TOMORROW.year, TOMORROW.month, TOMORROW.day)

SEARCH = "Flight Search Agent"
DETAILS = "Flight Details Agent"
TRAVEL = "Travel Assistant Agent"

# Free-tier pacing: Gemini free tier allows 15 requests/min, and each scenario
# fires ~2-3 LLM calls (triage -> specialist -> post-tool turn). We space
# scenarios out to stay under the limit and auto-retry if we still trip a 429,
# so the suite runs end-to-end on the free tier without a code change.
PACE_SECONDS = 13
RETRY_WAIT_SECONDS = 48
MAX_ATTEMPTS = 4


# ──────────────────────────────────────────────────────────────
# Ground truth pulled directly from the database (no LLM involved)
# ──────────────────────────────────────────────────────────────

async def ground_truth():
    async with AsyncSessionLocal() as s:
        dxb_econ = await FlightService.search_flights(s, "KHI", "DXB", TOMORROW_DT, CabinClass.ECONOMY)
        dxb_biz = await FlightService.search_flights(s, "KHI", "DXB", TOMORROW_DT, CabinClass.BUSINESS)
        ek = (await s.execute(select(Flight).where(Flight.flight_number == "EK-601"))).scalars().all()
    return {
        "dxb_econ_ids": {f.id for f in dxb_econ},
        "dxb_econ_prices": {round(f.total_price, 2) for f in dxb_econ},
        "dxb_biz_ids": {f.id for f in dxb_biz},
        "dxb_all_ids": {f.id for f in dxb_econ} | {f.id for f in dxb_biz},
        "ek601_ids": {f.id for f in ek},
        "ek601_prices": {round(f.total_price, 2) for f in ek},
    }


# ──────────────────────────────────────────────────────────────
# SDK-result introspection helpers (prove the handoff really happened)
# ──────────────────────────────────────────────────────────────

def handoff_targets(result) -> list[str]:
    """Names of agents handed off TO, taken from real SDK HandoffOutputItems."""
    out = []
    for it in result.new_items:
        if it.__class__.__name__ == "HandoffOutputItem":
            tgt = getattr(getattr(it, "target_agent", None), "name", None)
            if tgt:
                out.append(tgt)
    return out


def tool_calls(result) -> list[tuple[str, dict]]:
    out = []
    for it in result.new_items:
        if it.__class__.__name__ == "ToolCallItem":
            raw = getattr(it, "raw_item", None)
            name = getattr(raw, "name", None)
            args_str = getattr(raw, "arguments", None) or "{}"
            try:
                args = json.loads(args_str)
            except (ValueError, TypeError):
                args = {}
            if name:
                out.append((name, args))
    return out


def tool_names(calls) -> list[str]:
    return [n for n, _ in calls]


def cabin_args(calls) -> list[str]:
    return [str(a.get("cabin_class", "")).lower() for _, a in calls if "cabin_class" in a]


def called_any(calls, names) -> bool:
    return any(n in names for n, _ in calls)


_paced_once = False


async def run(user_input: str, context=None):
    """Start every scenario at the Triage Agent, pacing + retrying to respect
    the Gemini free-tier limit (15 req/min). Correctness is unaffected — only the
    cadence of calls changes."""
    global _paced_once
    if _paced_once:
        await asyncio.sleep(PACE_SECONDS)
    _paced_once = True

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await Runner.run(
                starting_agent=flight_triage_agent, input=user_input, context=context)
            return result, result.final_output, tool_calls(result)
        except RateLimitError:
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"    (free-tier rate limit hit; waiting {RETRY_WAIT_SECONDS}s "
                  f"then retrying — attempt {attempt + 1}/{MAX_ATTEMPTS})")
            await asyncio.sleep(RETRY_WAIT_SECONDS)


def report(label: str, checks: list[tuple[str, bool]], result, out) -> bool:
    ok = all(c[1] for c in checks)
    print(f"\n[{PASS if ok else FAIL}] {label}")
    for desc, passed in checks:
        print(f"    - [{'x' if passed else ' '}] {desc}")
    last = getattr(result.last_agent, "name", "?")
    print(f"    -> handoffs={handoff_targets(result)} last_agent='{last}' out={type(out).__name__}")
    if isinstance(out, FlightSearchResponse):
        print(f"    -> success={out.success} clarify={out.needs_clarification} n={len(out.flights)}")
    elif isinstance(out, FlightDetailsResponse):
        print(f"    -> success={out.success} flight={out.flight.flight_number if out.flight else None}")
    else:
        print(f"    -> text: {str(out)[:110]}")
    return ok


# ──────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────

async def main() -> None:
    gt = await ground_truth()
    results: list[bool] = []
    print("=" * 70)
    print("PHASE 8 — HANDOFFS + MULTI-AGENT ROUTING (live via Runner.run)")
    print(f"(ground truth {TOMORROW.isoformat()}: {len(gt['dxb_econ_ids'])} KHI->DXB economy, "
          f"{len(gt['dxb_biz_ids'])} business, {len(gt['ek601_ids'])} EK-601 rows)")
    print("=" * 70)

    # 1. Flight search routing
    result, out, calls = await run("Find flights from Karachi to Dubai tomorrow.")
    checks = [
        ("routed via SDK handoff to Flight Search Agent", SEARCH in handoff_targets(result)),
        ("last_agent is Flight Search Agent", result.last_agent.name == SEARCH),
        ("a search tool executed", called_any(calls, ("search_flights", "filter_flights"))),
        ("final output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse)),
    ]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("flights present", len(out.flights) > 0),
            ("all flight_ids are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)),
        ]
    results.append(report("1. Flight search routing", checks, result, out))

    # 2. Flight details routing
    result, out, calls = await run("Give me the details of EK-601.")
    checks = [
        ("routed via SDK handoff to Flight Details Agent", DETAILS in handoff_targets(result)),
        ("last_agent is Flight Details Agent", result.last_agent.name == DETAILS),
        ("a details lookup tool executed",
         called_any(calls, ("find_flight_by_number", "get_flight_details"))),
        ("final output is a valid FlightDetailsResponse", isinstance(out, FlightDetailsResponse)),
    ]
    if isinstance(out, FlightDetailsResponse):
        f = out.flight
        checks += [
            ("success is True", out.success is True),
            ("flight is populated", f is not None),
            ("flight_number is EK-601", bool(f) and f.flight_number == "EK-601"),
            ("airline is Emirates (real, not invented)", bool(f) and f.airline == "Emirates"),
            ("flight_id is a REAL EK-601 id", bool(f) and f.flight_id in gt["ek601_ids"]),
            ("price matches REAL EK-601 fare", bool(f) and round(f.price, 2) in gt["ek601_prices"]),
        ]
    results.append(report("2. Flight details routing", checks, result, out))

    # 3. General travel question
    result, out, calls = await run(
        "What is the difference between a direct flight and a connecting flight?")
    checks = [
        ("routed via SDK handoff to Travel Assistant Agent", TRAVEL in handoff_targets(result)),
        ("last_agent is Travel Assistant Agent", result.last_agent.name == TRAVEL),
        ("no flight search/details tool was called",
         not called_any(calls, ("search_flights", "filter_flights",
                                 "find_flight_by_number", "get_flight_details"))),
        ("answer is a non-empty general explanation", isinstance(out, str) and len(out.strip()) > 0),
    ]
    results.append(report("3. General travel question", checks, result, out))

    # 4. Search WITH context — context must survive the handoff
    ctx = FlightAssistantContext(user_name="Bilal", preferred_cabin_class="business",
                                 preferred_currency="USD")
    result, out, calls = await run("Find flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [
        ("routed to Flight Search Agent", result.last_agent.name == SEARCH),
        ("final output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse)),
        # Context survived handoff: the search agent applied the business preference.
        ("context survived handoff (business cabin searched)", "business" in cabin_args(calls)),
    ]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks.append(("all flight_ids are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)))
    results.append(report("4. Search with context (context survives handoff)", checks, result, out))

    # 5. Explicit preference override AFTER handoff
    ctx = FlightAssistantContext(preferred_cabin_class="business")
    result, out, calls = await run("Find economy flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [
        ("routed to Flight Search Agent", result.last_agent.name == SEARCH),
        ("final output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse)),
        ("explicit economy wins — business NOT in tool args", "business" not in cabin_args(calls)),
    ]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("economy flights present", len(out.flights) > 0),
            ("every returned flight is a REAL economy id", all(i in gt["dxb_econ_ids"] for i in ids)),
            ("NO business flight leaked", all(i not in gt["dxb_biz_ids"] for i in ids)),
        ]
    results.append(report("5. Explicit preference override after handoff", checks, result, out))

    # 6. Non-existent flight details — no fabrication
    result, out, calls = await run("Give me the details of flight XY-9999.")
    checks = [
        ("routed to Flight Details Agent", result.last_agent.name == DETAILS),
        ("a details lookup tool executed",
         called_any(calls, ("find_flight_by_number", "get_flight_details"))),
        ("final output is a valid FlightDetailsResponse", isinstance(out, FlightDetailsResponse)),
    ]
    if isinstance(out, FlightDetailsResponse):
        checks += [
            ("success is False", out.success is False),
            ("flight is None (no fabrication)", out.flight is None),
        ]
    results.append(report("6. Non-existent flight details", checks, result, out))

    # 7. Ambiguous request — must not invent a route (routed to Search -> clarifies)
    result, out, calls = await run("I need a flight.")
    checks = [
        ("routed to Flight Search Agent", result.last_agent.name == SEARCH),
        ("final output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse)),
    ]
    if isinstance(out, FlightSearchResponse):
        msg = out.message.lower()
        # Accept a question mark OR an explicit request for the missing details —
        # LLM phrasing of a clarifying prompt varies run to run.
        asks_for_info = ("?" in out.message) or any(
            kw in msg for kw in ("provide", "which", "where", "what", "let me know",
                                 "could you", "can you", "please specify", "departure",
                                 "destination", "origin"))
        checks += [
            ("needs_clarification is True", out.needs_clarification is True),
            ("flights list is EMPTY (no invented route)", out.flights == []),
            ("did NOT call a search tool", not called_any(calls, ("search_flights", "filter_flights"))),
            ("message asks for the missing details", asks_for_info),
        ]
    results.append(report("7. Ambiguous request", checks, result, out))

    # 8. Routing stability — a matrix of intents each reaches the right specialist
    matrix = [
        ("Show me non-stop flights from Karachi to Dubai tomorrow under $300.", SEARCH),
        ("What are the details of PK-201?", DETAILS),
        ("What does baggage allowance mean?", TRAVEL),
    ]
    stability_checks = []
    for text, expected in matrix:
        result, out, calls = await run(text)
        routed = expected in handoff_targets(result) and result.last_agent.name == expected
        stability_checks.append((f"'{text[:48]}...' -> {result.last_agent.name} (want {expected})", routed))
    ok8 = all(c[1] for c in stability_checks)
    print(f"\n[{PASS if ok8 else FAIL}] 8. Routing stability")
    for desc, passed in stability_checks:
        print(f"    - [{'x' if passed else ' '}] {desc}")
    results.append(ok8)

    # Summary
    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    print(f"RESULT: {passed}/{len(results)} scenarios passed")
    print("=" * 70)
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
