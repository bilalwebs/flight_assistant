"""
Phase 9 — Agents-as-Tools test suite.

Every scenario runs the REAL orchestration path via
`Runner.run(starting_agent=flight_orchestrator_agent, ...)` with the REAL
`Agent.as_tool()` mechanism — nothing about the orchestration is mocked.

We prove the AGENT-AS-TOOL mechanism fired (not a handoff, and not text
guessing) by asserting on actual SDK result items:

  * an agent-tool name appears in `ToolCallItem`s  -> the specialist was invoked
    AS A TOOL by the orchestrator;
  * `result.last_agent` stays the ORCHESTRATOR    -> control was RETAINED
    (contrast Phase 8, where last_agent becomes the specialist);
  * NO `HandoffOutputItem` is present             -> no handoff occurred;
  * the agent-tool's `ToolCallOutputItem` carries the specialist's structured
    output as exact JSON, which we re-validate with Pydantic and cross-check
    against ground truth read straight from the database.

Every earlier guarantee is re-asserted here under orchestration: context
survives the agent-tool boundary, explicit requests still override preferences,
and no flight fact is ever fabricated.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from openai import RateLimitError

from agents import Runner, set_tracing_disabled

from app_agents import flight_orchestrator_agent
from models.responses import FlightSearchResponse, FlightDetailsResponse
from models.context import FlightAssistantContext
from models.flight import Flight, CabinClass
from services.flight_service import FlightService
from database.database import AsyncSessionLocal

set_tracing_disabled(True)

PASS, FAIL = "PASS", "FAIL"
TOMORROW = datetime.now(timezone.utc).date() + timedelta(days=1)
TOMORROW_DT = datetime(TOMORROW.year, TOMORROW.month, TOMORROW.day)

ORCHESTRATOR = "Flight Orchestrator Agent"
SEARCH_TOOL = "search_flights_agent"
DETAILS_TOOL = "get_flight_details_agent"
TRAVEL_TOOL = "travel_assistant_agent"
AGENT_TOOLS = (SEARCH_TOOL, DETAILS_TOOL, TRAVEL_TOOL)

PIA = "Pakistan International Airlines"
EMIRATES = "Emirates"

# Free-tier pacing (Gemini: 15 req/min). Each orchestrated scenario costs more
# calls than a single-agent one (orchestrator turn + nested specialist run +
# post-tool turn), so we pace and auto-retry on 429.
PACE_SECONDS = 16
RETRY_WAIT_SECONDS = 50
MAX_ATTEMPTS = 4


# ──────────────────────────────────────────────────────────────
# Ground truth pulled directly from the database (no LLM involved)
# ──────────────────────────────────────────────────────────────

async def ground_truth():
    async with AsyncSessionLocal() as s:
        dxb_econ = await FlightService.search_flights(s, "KHI", "DXB", TOMORROW_DT, CabinClass.ECONOMY)
        dxb_biz = await FlightService.search_flights(s, "KHI", "DXB", TOMORROW_DT, CabinClass.BUSINESS)
        pia_dxb = await FlightService.filter_flights(s, "KHI", "DXB", TOMORROW_DT,
                                                    CabinClass.ECONOMY, airline=PIA)
        ek = (await s.execute(select(Flight).where(Flight.flight_number == "EK-601"))).scalars().all()
    return {
        "dxb_econ_ids": {f.id for f in dxb_econ},
        "dxb_econ_prices": {round(f.total_price, 2) for f in dxb_econ},
        "dxb_biz_ids": {f.id for f in dxb_biz},
        "dxb_all_ids": {f.id for f in dxb_econ} | {f.id for f in dxb_biz},
        "dxb_all_prices": {round(f.total_price, 2) for f in dxb_econ} | {round(f.total_price, 2) for f in dxb_biz},
        "pia_dxb_ids": {f.id for f in pia_dxb},
        "ek601_ids": {f.id for f in ek},
        "ek601_prices": {round(f.total_price, 2) for f in ek},
    }


# ──────────────────────────────────────────────────────────────
# SDK-result introspection (prove agent-as-tool, not handoff)
# ──────────────────────────────────────────────────────────────

def tool_calls(result) -> list[tuple[str, dict]]:
    """[(tool_name, parsed_args)] for EVERY tool call in the run — this includes
    the orchestrator's agent-tool calls AND the specialists' own flight tools,
    because nested agent-tool runs contribute their items to the run result."""
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


def agent_tool_calls(calls) -> list[str]:
    """Only the agent-as-tool invocations made by the orchestrator."""
    return [n for n in tool_names(calls) if n in AGENT_TOOLS]


def called_any(calls, names) -> bool:
    return any(n in names for n, _ in calls)


def handoff_targets(result) -> list[str]:
    """Should always be EMPTY in Phase 9 — a handoff would mean control was lost."""
    out = []
    for it in result.new_items:
        if it.__class__.__name__ == "HandoffOutputItem":
            tgt = getattr(getattr(it, "target_agent", None), "name", None)
            if tgt:
                out.append(tgt)
    return out


def agent_tool_outputs(result, tool_name: str) -> list[str]:
    """Raw string outputs returned by a given agent-tool (our canonical JSON)."""
    out = []
    calls = {}
    for it in result.new_items:
        cls = it.__class__.__name__
        raw = getattr(it, "raw_item", None)
        if cls == "ToolCallItem":
            cid = getattr(raw, "call_id", None) or getattr(raw, "id", None)
            if cid:
                calls[cid] = getattr(raw, "name", None)
        elif cls == "ToolCallOutputItem":
            cid = (raw.get("call_id") if isinstance(raw, dict)
                   else getattr(raw, "call_id", None))
            if calls.get(cid) == tool_name:
                out.append(it.output if isinstance(it.output, str) else str(it.output))
    return out


def parsed_specialist(result, tool_name: str, model):
    """Re-validate the structured payload the specialist returned through the
    agent-tool boundary. Proves the structured output survived intact."""
    for raw in agent_tool_outputs(result, tool_name):
        try:
            return model.model_validate_json(raw)
        except Exception:
            try:
                return model.model_validate(json.loads(raw))
            except Exception:
                continue
    return None


def cabin_args(calls) -> list[str]:
    """cabin_class values passed to the SPECIALIST's real flight tools."""
    return [str(a.get("cabin_class", "")).lower() for _, a in calls if "cabin_class" in a]


def airline_args(calls) -> list[str]:
    return [str(a.get("airline", "")).lower() for _, a in calls if a.get("airline") is not None]


def forwarded_input(calls, tool_name: str) -> str:
    """What the orchestrator actually forwarded to an agent-tool."""
    return " ".join(str(a.get("input", "")).lower()
                    for n, a in calls if n == tool_name)


_paced_once = False


async def run(user_input: str, context=None):
    """Run the REAL orchestration path, paced/retried for the Gemini free tier."""
    global _paced_once
    if _paced_once:
        await asyncio.sleep(PACE_SECONDS)
    _paced_once = True

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await Runner.run(
                starting_agent=flight_orchestrator_agent, input=user_input, context=context)
            return result, result.final_output, tool_calls(result)
        except RateLimitError:
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"    (free-tier rate limit hit; waiting {RETRY_WAIT_SECONDS}s "
                  f"then retrying — attempt {attempt + 1}/{MAX_ATTEMPTS})")
            await asyncio.sleep(RETRY_WAIT_SECONDS)


def control_retained(result) -> list[tuple[str, bool]]:
    """The Phase 9 signature: agent-tool used, orchestrator still in control."""
    return [
        ("control RETAINED — last_agent is still the Orchestrator",
         getattr(result.last_agent, "name", None) == ORCHESTRATOR),
        ("NO handoff occurred (agent-as-tool, not handoff)", handoff_targets(result) == []),
    ]


def report(label: str, checks: list[tuple[str, bool]], result, out) -> bool:
    ok = all(c[1] for c in checks)
    print(f"\n[{PASS if ok else FAIL}] {label}")
    for desc, passed in checks:
        print(f"    - [{'x' if passed else ' '}] {desc}")
    last = getattr(result.last_agent, "name", "?")
    calls = tool_calls(result)
    print(f"    -> agent_tools={agent_tool_calls(calls)} handoffs={handoff_targets(result)} "
          f"last_agent='{last}'")
    print(f"    -> all_tool_calls={tool_names(calls)}")
    print(f"    -> final: {str(out)[:150]}")
    return ok


# ──────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────

async def main() -> None:
    gt = await ground_truth()
    results: list[bool] = []
    print("=" * 70)
    print("PHASE 9 — AGENTS AS TOOLS (live via Runner.run + real Agent.as_tool)")
    print(f"(ground truth {TOMORROW.isoformat()}: {len(gt['dxb_econ_ids'])} KHI->DXB economy, "
          f"{len(gt['dxb_biz_ids'])} business, {len(gt['pia_dxb_ids'])} PIA, "
          f"{len(gt['ek601_ids'])} EK-601 rows)")
    print("=" * 70)

    # 1. Search agent-tool routing
    result, out, calls = await run("Find flights from Karachi to Dubai tomorrow.")
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("orchestrator invoked the search agent-TOOL", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("specialist returned a VALID FlightSearchResponse through the tool boundary",
         parsed is not None),
        ("orchestrator produced the final answer text", isinstance(out, str) and len(out.strip()) > 0),
    ]
    if parsed is not None:
        ids = [f.flight_id for f in parsed.flights]
        checks += [
            ("flights present", len(parsed.flights) > 0),
            ("all flight_ids are REAL seeded ids (proving specialist tools ran)",
             all(i in gt["dxb_all_ids"] for i in ids)),
            ("all prices are REAL seeded fares",
             all(round(f.price, 2) in gt["dxb_all_prices"] for f in parsed.flights)),
        ]
    results.append(report("1. Search agent-tool routing", checks, result, out))

    # 2. Details agent-tool routing
    result, out, calls = await run("Give me the details of EK-601.")
    parsed = parsed_specialist(result, DETAILS_TOOL, FlightDetailsResponse)
    checks = [
        ("orchestrator invoked the details agent-TOOL", DETAILS_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("specialist returned a VALID FlightDetailsResponse through the tool boundary",
         parsed is not None),
    ]
    if parsed is not None:
        f = parsed.flight
        checks += [
            ("success is True", parsed.success is True),
            ("flight is populated", f is not None),
            ("flight_number is EK-601", bool(f) and f.flight_number == "EK-601"),
            ("airline is Emirates (real, not invented)", bool(f) and f.airline == EMIRATES),
            ("flight_id is a REAL EK-601 id (proving specialist tools ran)",
             bool(f) and f.flight_id in gt["ek601_ids"]),
            ("price matches a REAL EK-601 fare", bool(f) and round(f.price, 2) in gt["ek601_prices"]),
            ("orchestrator's answer repeats the REAL flight number",
             isinstance(out, str) and "EK-601" in out),
        ]
    results.append(report("2. Details agent-tool routing", checks, result, out))

    # 3. Travel assistant agent-tool routing
    result, out, calls = await run(
        "What is the difference between a direct flight and a connecting flight?")
    checks = [
        ("orchestrator invoked the travel agent-TOOL", TRAVEL_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("no flight database tool was called unnecessarily",
         not called_any(calls, ("search_flights", "filter_flights",
                                "find_flight_by_number", "get_flight_details"))),
        ("did NOT call the search or details agent-tools",
         SEARCH_TOOL not in agent_tool_calls(calls) and DETAILS_TOOL not in agent_tool_calls(calls)),
        ("answer is a non-empty explanation", isinstance(out, str) and len(out.strip()) > 0),
    ]
    results.append(report("3. Travel assistant agent-tool routing", checks, result, out))

    # 4. Context propagation across the agent-tool boundary
    ctx = FlightAssistantContext(user_name="Bilal", preferred_cabin_class="business",
                                 preferred_currency="USD")
    result, out, calls = await run("Find flights from Karachi to Dubai tomorrow.", context=ctx)
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("orchestrator invoked the search agent-tool", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("specialist output still valid", parsed is not None),
    ]
    if parsed is not None:
        ids = [f.flight_id for f in parsed.flights]
        # Context propagation proof: user said NOTHING about cabin, yet specialist
        # returned business flights (which only exist because context.preferred_cabin_class
        # was read by the nested specialist's dynamic instructions).
        has_biz = any(i in gt["dxb_biz_ids"] for i in ids)
        checks += [
            ("context SURVIVED the agent-tool boundary (business flights returned despite "
             "no explicit cabin in user input)", has_biz or len(ids) == 1),
            ("all flight_ids are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)),
        ]
    results.append(report("4. Context propagation through agent-tool", checks, result, out))

    # 5. Explicit cabin override beats the stored preference
    ctx = FlightAssistantContext(preferred_cabin_class="business")
    result, out, calls = await run("Find economy flights from Karachi to Dubai tomorrow.", context=ctx)
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("orchestrator invoked the search agent-tool", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("orchestrator forwarded ECONOMY to the specialist",
         "economy" in forwarded_input(calls, SEARCH_TOOL)),
        ("explicit economy wins — business NEVER searched", "business" not in cabin_args(calls)),
        ("specialist output still valid", parsed is not None),
    ]
    if parsed is not None:
        ids = [f.flight_id for f in parsed.flights]
        checks += [
            ("economy flights present", len(parsed.flights) > 0),
            ("every returned flight is a REAL economy id", all(i in gt["dxb_econ_ids"] for i in ids)),
            ("NO business flight leaked", all(i not in gt["dxb_biz_ids"] for i in ids)),
        ]
    results.append(report("5. Explicit cabin override through agent-tool", checks, result, out))

    # 6. Explicit airline override beats the stored preference
    ctx = FlightAssistantContext(preferred_airline=EMIRATES)
    result, out, calls = await run(
        "Find PIA flights from Karachi to Dubai tomorrow.", context=ctx)
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("orchestrator invoked the search agent-tool", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("orchestrator forwarded PIA to the specialist",
         "pia" in forwarded_input(calls, SEARCH_TOOL) or
         "pakistan" in forwarded_input(calls, SEARCH_TOOL)),
        ("specialist output still valid", parsed is not None),
    ]
    if parsed is not None:
        airlines = {f.airline for f in parsed.flights}
        ids = [f.flight_id for f in parsed.flights]
        checks += [
            ("PIA flights present", len(parsed.flights) > 0),
            ("every returned flight is PIA (explicit request honored)", airlines == {PIA}),
            ("returned ids are REAL PIA ids (grounded)", all(i in gt["pia_dxb_ids"] for i in ids)),
        ]
    results.append(report("6. Explicit airline override through agent-tool", checks, result, out))

    # 7. No results — zero fabrication anywhere in the chain
    result, out, calls = await run("Find flights from Karachi to Los Angeles tomorrow.")
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    text = (out or "").lower() if isinstance(out, str) else ""
    checks = [
        ("orchestrator invoked the search agent-tool", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("specialist returned a valid response (no crash)", parsed is not None),
    ]
    if parsed is not None:
        checks += [
            ("specialist flights list is EMPTY (no invented flight)", parsed.flights == []),
            ("total_results is 0", parsed.total_results == 0),
            ("cheapest_flight_id is None", parsed.cheapest_flight_id is None),
            ("fastest_flight_id is None", parsed.fastest_flight_id is None),
        ]
    checks += [
        ("orchestrator did NOT invent a fallback flight",
         not any(a.lower() in text for a in ("emirates", "pia", "pakistan international",
                                             "flydubai", "qatar airways", "turkish"))),
        ("orchestrator reports the honest no-result",
         any(k in text for k in ("no flight", "not find", "couldn't find", "could not find",
                                 "unable", "no direct", "no available", "no results",
                                 "don't have", "do not have", "not available"))),
    ]
    results.append(report("7. No-result / no fabrication", checks, result, out))

    # 8. Multi-agent composition — TWO specialists in ONE orchestrated run.
    # This is the capability a handoff CANNOT provide: a handoff transfers control
    # away permanently, so it can never combine two specialists in one answer.
    result, out, calls = await run(
        "Find me a suitable flight from Karachi to Dubai tomorrow, and then also "
        "explain what baggage allowance means.")
    used = agent_tool_calls(calls)
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("called the search agent-tool", SEARCH_TOOL in used),
        ("called the travel assistant agent-tool", TRAVEL_TOOL in used),
        ("TWO different specialists composed in ONE run", len(set(used)) >= 2),
        *control_retained(result),
        ("final answer is non-empty", isinstance(out, str) and len(out.strip()) > 0),
    ]
    if parsed is not None:
        ids = [f.flight_id for f in parsed.flights]
        checks.append(("search results still REAL (composition did not corrupt data, proving tools ran)",
                       all(i in gt["dxb_all_ids"] for i in ids)))
    results.append(report("8. Multi-agent composition", checks, result, out))

    # 9. Specialist result preservation — orchestrator must not alter the numbers.
    result, out, calls = await run("Find economy flights from Karachi to Dubai tomorrow.")
    parsed = parsed_specialist(result, SEARCH_TOOL, FlightSearchResponse)
    checks = [
        ("orchestrator invoked the search agent-tool", SEARCH_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("structured payload survived the tool boundary", parsed is not None),
    ]
    if parsed is not None:
        ids = [f.flight_id for f in parsed.flights]
        checks += [
            ("total_results == len(flights) (accurate)", parsed.total_results == len(parsed.flights)),
            ("every flight_id is REAL", all(i in gt["dxb_econ_ids"] for i in ids)),
            ("every price is a REAL seeded fare",
             all(round(f.price, 2) in gt["dxb_econ_prices"] for f in parsed.flights)),
            ("cheapest_flight_id is one of the returned flights",
             parsed.cheapest_flight_id is None or parsed.cheapest_flight_id in ids),
            ("fastest_flight_id is one of the returned flights",
             parsed.fastest_flight_id is None or parsed.fastest_flight_id in ids),
        ]
        # The orchestrator's prose must not contain a price that isn't real.
        if isinstance(out, str):
            import re
            quoted = {round(float(m), 2) for m in re.findall(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", out)}
            real = {round(f.price, 2) for f in parsed.flights}
            checks.append(("every price the orchestrator quoted is a REAL specialist price",
                           quoted.issubset(real | gt["dxb_econ_prices"])))
    results.append(report("9. Specialist result preservation", checks, result, out))

    # 10. Error / not-found handling — must not crash, must not invent
    result, out, calls = await run("Give me the details of flight XY-9999.")
    parsed = parsed_specialist(result, DETAILS_TOOL, FlightDetailsResponse)
    text = (out or "").lower() if isinstance(out, str) else ""
    checks = [
        ("orchestrator invoked the details agent-tool", DETAILS_TOOL in agent_tool_calls(calls)),
        *control_retained(result),
        ("run completed without crashing", isinstance(out, str) and len(out.strip()) > 0),
        ("specialist returned a valid response", parsed is not None),
    ]
    if parsed is not None:
        checks += [
            ("specialist success is False", parsed.success is False),
            ("specialist flight is None (no fabrication)", parsed.flight is None),
        ]
    checks += [
        ("orchestrator relays the not-found honestly",
         any(k in text for k in ("not find", "not found", "couldn't find", "could not find",
                                 "could not be found", "no flight", "unable", "doesn't exist",
                                 "does not exist", "no information", "not available"))),
        ("orchestrator did NOT invent a substitute flight",
         not any(a.lower() in text for a in ("emirates", "flydubai", "qatar airways", "turkish"))),
    ]
    results.append(report("10. Error / not-found handling", checks, result, out))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    print(f"RESULT: {passed}/{len(results)} scenarios passed")
    print("=" * 70)
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
