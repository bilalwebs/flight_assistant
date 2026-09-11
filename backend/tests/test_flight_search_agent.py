"""
Phase 7 — Context + Dynamic Instructions test suite (supersedes the Phase 6
structured-output suite in place; every Phase 6 guarantee is still asserted
here — valid FlightSearchResponse, DB-grounded flights, honest no-results, and
clarification without fabrication — now under real Agent Context).

Every scenario runs the REAL agent via `Runner.run(..., context=...)`, passing a
`FlightAssistantContext`. We assert that:
  * result.final_output is a VALID FlightSearchResponse (Pydantic-validated),
  * preferences INFLUENCE the search (proven by inspecting the actual tool-call
    arguments the agent sent — e.g. cabin_class="business"),
  * an EXPLICIT user request always OVERRIDES the matching preference,
  * context NEVER fabricates: every populated flight is grounded in real seeded
    data (flight_id/price must match rows fetched straight from the DB), and
  * missing context / missing required fields degrade gracefully.

Ground truth is pulled live from the DB for the ACTUAL 'tomorrow' date, so the
suite is independent of when the database was seeded.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta

from openai import RateLimitError

from agents import Runner, set_tracing_disabled

from app_agents import flight_search_agent
from models.responses import FlightSearchResponse
from models.flight import CabinClass
from models.context import FlightAssistantContext
from services.flight_service import FlightService
from database.database import AsyncSessionLocal

set_tracing_disabled(True)

PASS, FAIL = "PASS", "FAIL"
TOMORROW = datetime.now(timezone.utc).date() + timedelta(days=1)
TOMORROW_DT = datetime(TOMORROW.year, TOMORROW.month, TOMORROW.day)

PIA = "Pakistan International Airlines"
EMIRATES = "Emirates"

# Free-tier pacing (Gemini: 15 req/min). Space scenarios out and auto-retry on
# a 429 so the suite runs end-to-end on the free tier without a code change.
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
        ist_econ = await FlightService.search_flights(s, "KHI", "IST", TOMORROW_DT, CabinClass.ECONOMY)
        pia_dxb = await FlightService.filter_flights(s, "KHI", "DXB", TOMORROW_DT,
                                                     CabinClass.ECONOMY, airline=PIA)
    return {
        "dxb_econ_ids": {f.id for f in dxb_econ},
        "dxb_econ_prices": {round(f.total_price, 2) for f in dxb_econ},
        "dxb_biz_ids": {f.id for f in dxb_biz},
        "dxb_biz_prices": {round(f.total_price, 2) for f in dxb_biz},
        "dxb_all_ids": {f.id for f in dxb_econ} | {f.id for f in dxb_biz},
        "dxb_all_prices": {round(f.total_price, 2) for f in dxb_econ} | {round(f.total_price, 2) for f in dxb_biz},
        "ist_econ_ids": {f.id for f in ist_econ},
        "pia_dxb_ids": {f.id for f in pia_dxb},
    }


# ──────────────────────────────────────────────────────────────
# Runner + introspection helpers
# ──────────────────────────────────────────────────────────────

def tool_calls(result) -> list[tuple[str, dict]]:
    """Return [(tool_name, parsed_arguments), ...] for every tool the agent called."""
    out = []
    for item in result.new_items:
        if item.__class__.__name__ == "ToolCallItem":
            raw = getattr(item, "raw_item", None)
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


def called_search(calls) -> bool:
    return any(n in ("search_flights", "filter_flights") for n, _ in calls)


def arg_values(calls, key) -> list[str]:
    return [str(a.get(key, "")).lower() for _, a in calls if a.get(key) is not None]


_paced_once = False


async def run(user_input: str, context=None):
    """Run the agent, pacing + retrying to respect the Gemini free-tier limit
    (15 req/min). Correctness is unaffected — only the cadence of calls changes."""
    global _paced_once
    if _paced_once:
        await asyncio.sleep(PACE_SECONDS)
    _paced_once = True

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await Runner.run(
                starting_agent=flight_search_agent, input=user_input, context=context)
            return result, result.final_output, tool_calls(result)
        except RateLimitError:
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"    (free-tier rate limit hit; waiting {RETRY_WAIT_SECONDS}s "
                  f"then retrying — attempt {attempt + 1}/{MAX_ATTEMPTS})")
            await asyncio.sleep(RETRY_WAIT_SECONDS)


def report(label: str, checks: list[tuple[str, bool]], out) -> bool:
    ok = all(c[1] for c in checks)
    print(f"\n[{PASS if ok else FAIL}] {label}")
    for desc, passed in checks:
        print(f"    - [{'x' if passed else ' '}] {desc}")
    if isinstance(out, FlightSearchResponse):
        print(f"    -> success={out.success} clarify={out.needs_clarification} "
              f"n={len(out.flights)} total={out.total_results} "
              f"cheapest={out.cheapest_flight_id is not None} fastest={out.fastest_flight_id is not None}")
        print(f"    -> message: {out.message[:110]}")
    return ok


# ──────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────

async def main() -> None:
    gt = await ground_truth()
    results: list[bool] = []
    print("=" * 70)
    print("PHASE 7 — CONTEXT + DYNAMIC INSTRUCTIONS (live via Runner.run)")
    print(f"(ground truth for {TOMORROW.isoformat()}: "
          f"{len(gt['dxb_econ_ids'])} KHI->DXB economy, {len(gt['dxb_biz_ids'])} business, "
          f"{len(gt['ist_econ_ids'])} KHI->IST economy)")
    print("=" * 70)

    # 1. Context is received — normal request runs and returns structured output
    ctx = FlightAssistantContext(user_name="Bilal", preferred_cabin_class="business",
                                 preferred_currency="USD")
    _, out, calls = await run("Find me flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("agent executed a search tool", called_search(calls)),
            ("total_results == len(flights)", out.total_results == len(out.flights)),
            ("all populated flights are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)),
        ]
    results.append(report("1. Context is received", checks, out))

    # 2. Cabin preference influences an ambiguous request (no cabin stated by user)
    ctx = FlightAssistantContext(preferred_cabin_class="business")
    _, out, calls = await run("Find flights from Karachi to Dubai tomorrow.", context=ctx)
    ids = [f.flight_id for f in out.flights] if isinstance(out, FlightSearchResponse) else []
    considered = ("business" in arg_values(calls, "cabin_class")) or bool(
        gt["dxb_biz_ids"] and any(i in gt["dxb_biz_ids"] for i in ids))
    checks = [
        ("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse)),
        ("preference CONSIDERED (business cabin searched or returned)", considered),
        # grounded either way — no fabrication regardless of whether business exists tomorrow
        ("all populated flights are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)),
    ]
    results.append(report("2. Cabin preference influences ambiguous request", checks, out))

    # 3. Explicit ECONOMY request overrides the business preference
    ctx = FlightAssistantContext(preferred_cabin_class="business")
    _, out, calls = await run("Find economy flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("did NOT search the business cabin", "business" not in arg_values(calls, "cabin_class")),
            ("economy flights present", len(out.flights) > 0),
            ("every returned flight is a REAL economy id", all(i in gt["dxb_econ_ids"] for i in ids)),
            ("NO business flight leaked into results", all(i not in gt["dxb_biz_ids"] for i in ids)),
        ]
    results.append(report("3. Explicit economy overrides cabin preference", checks, out))

    # 4. Explicit airline request overrides preferred airline
    ctx = FlightAssistantContext(preferred_airline=EMIRATES)
    _, out, calls = await run(
        "Show me Pakistan International Airlines flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        airlines = {f.airline for f in out.flights}
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("did NOT filter by the preferred airline (Emirates)",
             all("emirates" not in v for v in arg_values(calls, "airline"))),
            ("PIA flights present", len(out.flights) > 0),
            ("every returned flight is PIA (explicit request honored)", airlines == {PIA}),
            ("returned ids subset of REAL PIA set (grounded)", all(i in gt["pia_dxb_ids"] for i in ids)),
        ]
    results.append(report("4. Explicit airline overrides preferred airline", checks, out))

    # 5. Context preference absent from data must NOT fabricate flights
    ctx = FlightAssistantContext(preferred_airline="Singapore Airlines")
    _, out, calls = await run("Find flights from Karachi to Dubai tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        prices = [round(f.price, 2) for f in out.flights]
        checks += [
            ("every returned id is a REAL seeded id", all(i in gt["dxb_all_ids"] for i in ids)),
            ("every returned price matches REAL seeded fares", all(p in gt["dxb_all_prices"] for p in prices)),
            ("NO fabricated 'Singapore Airlines' flight appears",
             all(f.airline != "Singapore Airlines" for f in out.flights)),
        ]
    results.append(report("5. Context does not fabricate flights", checks, out))

    # 6. Missing context still works exactly like Phase 6
    _, out, calls = await run("Find me flights from Karachi to Dubai tomorrow.", context=None)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        ids = [f.flight_id for f in out.flights]
        checks += [
            ("no crash with no context", True),
            ("normal search works — flights present", len(out.flights) > 0),
            ("total_results == len(flights)", out.total_results == len(out.flights)),
            ("all populated flights are REAL seeded ids", all(i in gt["dxb_all_ids"] for i in ids)),
        ]
    results.append(report("6. Missing context still works", checks, out))

    # 7. Clarification with context — context must not fill a missing REQUIRED field
    ctx = FlightAssistantContext(user_name="Bilal", preferred_cabin_class="business",
                                 preferred_airline=EMIRATES)
    _, out, calls = await run("Find me a flight tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        msg = out.message.lower()
        # A valid clarification either ends with a question mark OR explicitly
        # requests the missing info (LLM phrasing varies — "Please provide your
        # departure city..." is just as valid a clarifying prompt as "...?").
        asks_for_info = ("?" in out.message) or any(
            kw in msg for kw in ("provide", "which", "where", "what", "let me know",
                                 "could you", "can you", "please specify", "departure",
                                 "destination", "origin"))
        checks += [
            ("needs_clarification is True", out.needs_clarification is True),
            ("flights list is EMPTY (no fabrication)", out.flights == []),
            ("did NOT call a search tool", not called_search(calls)),
            ("message asks for the missing details", asks_for_info),
        ]
    results.append(report("7. Clarification with context", checks, out))

    # 8. No-result search with context — honest empty, zero fabrication
    ctx = FlightAssistantContext(user_name="Bilal", preferred_cabin_class="business")
    _, out, calls = await run("Find me a flight from Karachi to Los Angeles tomorrow.", context=ctx)
    checks = [("final_output is a valid FlightSearchResponse", isinstance(out, FlightSearchResponse))]
    if isinstance(out, FlightSearchResponse):
        checks += [
            ("success is False", out.success is False),
            ("flights list is EMPTY (no fabrication)", out.flights == []),
            ("total_results == 0", out.total_results == 0),
            ("cheapest_flight_id is None", out.cheapest_flight_id is None),
            ("fastest_flight_id is None", out.fastest_flight_id is None),
        ]
    results.append(report("8. No-result search with context", checks, out))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    print(f"RESULT: {passed}/{len(results)} scenarios passed")
    print("=" * 70)
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
