"""Phase 11A — Guarded Flight Tools & Tool Guardrail regression tests.

Covers the production blocker found in Phase 11:
  1. The already-decorated `validate_flight_tool_inputs` must NOT be
     double-wrapped inside another ToolInputGuardrail(...).
  2. Guarding tools must NOT mutate the shared unguarded tools from
     tools.flight_tools.
  3. `data.context.tool_arguments` may arrive as a raw JSON string (not a
     dict); the guardrail must normalize it safely and never silently bypass
     validation.

Focused checks:
A. Already-decorated guardrail is not double-wrapped.
B. Original tools from tools.flight_tools are not mutated.
C. Guarded tools have the intended guardrail.
D. tool_arguments supplied as a dict works.
E. tool_arguments supplied as a JSON string works.
F. Empty/null tool_arguments is handled safely.
G. Malformed JSON does not bypass validation.
H. Unexpected argument types do not bypass validation.
I. Existing guardrail rules still reject invalid flight tool arguments.
J. Valid flight tool arguments still pass.
K. Integration: REAL Agents SDK path user request -> agent -> guarded tool ->
   guardrail -> tool -> FlightService -> structured result -> agent response.
"""
import asyncio
import json
import os
import sys
import tempfile
from types import SimpleNamespace

# Use the Gemini provider for the model-backed integration test with the same
# model that runs in production (gemini-3.5-flash-lite), so the guarded-tool
# path is exercised end-to-end through the exact production model. If the
# free-tier quota is exhausted the integration test reports QUOTA-BLOCKED,
# which must never be conflated with a code failure.
os.environ.setdefault("DEFAULT_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")

_test_db = os.path.join(tempfile.gettempdir(), "p11a_fix.db").replace("\\", "/")
os.environ["TEST_DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"

from agents import Agent, Runner, set_tracing_disabled  # noqa: E402
from agents.tool_guardrails import ToolInputGuardrail  # noqa: E402

# The decorated guardrail (a ToolInputGuardrail instance) and its raw function.
from guardrails.tool_guardrails import (  # noqa: E402
    validate_flight_tool_inputs,
    _normalize_tool_arguments,
)
from tools import flight_tools  # noqa: E402
from tools.guarded_flight_tools import GUARDED_FLIGHT_TOOLS  # noqa: E402
from tools.flight_tools import search_flights  # noqa: E402

set_tracing_disabled(True)

_guard = validate_flight_tool_inputs.guardrail_function
_EXPECTED_GUARDED_TOOLS = [
    "search_flights",
    "filter_flights",
    "get_flight_details",
    "find_flight_by_number",
    "compare_flights",
    "calculate_flight_price",
    "check_seat_availability",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"    [PASS] {name}")
    else:
        print(f"    [FAIL] {name}  {detail}")
        failures.append(name)


def ctx_for(tool_name, tool_arguments):
    return SimpleNamespace(context=SimpleNamespace(
        tool_name=tool_name,
        tool_arguments=tool_arguments,
    ))


def behavior(result):
    return result.behavior["type"]


# ────────────────────────────────────────────────────────────────────────────
# A. Already-decorated guardrail is not double-wrapped.
# ────────────────────────────────────────────────────────────────────────────
def test_a_no_double_wrap():
    print("\nA. Guardrail decorator shape")
    check("validate_flight_tool_inputs is a ToolInputGuardrail instance",
          isinstance(validate_flight_tool_inputs, ToolInputGuardrail))
    check("its guardrail_function is callable",
          callable(validate_flight_tool_inputs.guardrail_function))
    check("its guardrail_function is NOT itself a ToolInputGuardrail",
          not isinstance(validate_flight_tool_inputs.guardrail_function, ToolInputGuardrail))


# ────────────────────────────────────────────────────────────────────────────
# B. Original tools from tools.flight_tools are not mutated.
# ────────────────────────────────────────────────────────────────────────────
def test_b_originals_unmutated():
    print("\nB. Shared unguarded tools stay unmutated")
    originals = [
        flight_tools.search_flights,
        flight_tools.filter_flights,
        flight_tools.get_flight_details,
        flight_tools.find_flight_by_number,
        flight_tools.compare_flights,
        flight_tools.calculate_flight_price,
        flight_tools.check_seat_availability,
    ]
    for tool in originals:
        check(f"{tool.name} has no tool_input_guardrails",
              tool.tool_input_guardrails is None,
              f"got {tool.tool_input_guardrails}")
    check("guarded search_flights is a distinct instance (not the original)",
          _guarded("search_flights") is not search_flights)


def _guarded(name):
    return next(t for t in GUARDED_FLIGHT_TOOLS if t.name == name)


# ────────────────────────────────────────────────────────────────────────────
# C. Guarded tools have the intended guardrail.
# ────────────────────────────────────────────────────────────────────────────
def test_c_guarded_shape():
    print("\nC. Guarded tools carry the intended guardrail")
    originals_by_name = {t.name: t for t in [
        flight_tools.search_flights,
        flight_tools.filter_flights,
        flight_tools.get_flight_details,
        flight_tools.find_flight_by_number,
        flight_tools.compare_flights,
        flight_tools.calculate_flight_price,
        flight_tools.check_seat_availability,
    ]}
    for name in _EXPECTED_GUARDED_TOOLS:
        tool = _guarded(name)
        check(f"{name} exists in GUARDED_FLIGHT_TOOLS", tool is not None)
        guardrails = tool.tool_input_guardrails or []
        check(f"{name} has exactly one guardrail", len(guardrails) == 1, f"got {len(guardrails)}")
        if guardrails:
            entry = guardrails[0]
            check(f"{name} guardrail is the SAME decorated instance",
                  entry is validate_flight_tool_inputs)
            check(f"{name} guardrail_function is callable",
                  callable(entry.guardrail_function))
            check(f"{name} guardrail is NOT double-wrapped",
                  not isinstance(entry.guardrail_function, ToolInputGuardrail))
        check(f"{name} params schema preserved",
              tool.params_json_schema == originals_by_name[name].params_json_schema)


# ────────────────────────────────────────────────────────────────────────────
# D. tool_arguments supplied as a dict works.
# ────────────────────────────────────────────────────────────────────────────
def test_d_dict_args():
    print("\nD. dict tool_arguments")
    result = _guard(ctx_for("search_flights", {
        "origin": "KHI",
        "destination": "DXB",
        "departure_date": "2026-09-13",
        "passengers": 1,
        "cabin_class": "economy",
    }))
    check("valid dict => allow", behavior(result) == "allow", str(result.behavior))


# ────────────────────────────────────────────────────────────────────────────
# E. tool_arguments supplied as a JSON string works.
# ────────────────────────────────────────────────────────────────────────────
def test_e_json_string_args():
    print("\nE. JSON-string tool_arguments")
    raw = json.dumps({
        "origin": "KHI",
        "destination": "DXB",
        "departure_date": "2026-09-13",
        "passengers": 1,
        "cabin_class": "economy",
    })
    check("_normalize_tool_arguments parses JSON string",
          _normalize_tool_arguments(raw) == json.loads(raw))
    result = _guard(ctx_for("search_flights", raw))
    check("valid JSON string => allow", behavior(result) == "allow", str(result.behavior))


# ────────────────────────────────────────────────────────────────────────────
# F. Empty/null tool_arguments is handled safely.
# ────────────────────────────────────────────────────────────────────────────
def test_f_empty_null():
    print("\nF. empty / null tool_arguments")
    check("None -> {}",
          _normalize_tool_arguments(None) == {})
    check("empty string -> {}",
          _normalize_tool_arguments("") == {})
    check("whitespace string -> {}",
          _normalize_tool_arguments("   ") == {})
    r = _guard(ctx_for("search_flights", None))
    check("None args never allowed through (missing origin rejects)",
          behavior(r) == "reject_content", str(r.behavior))
    r2 = _guard(ctx_for("search_flights", ""))
    check("empty string args never allowed through (missing origin rejects)",
          behavior(r2) == "reject_content", str(r2.behavior))


# ────────────────────────────────────────────────────────────────────────────
# G. Malformed JSON does not bypass validation.
# ────────────────────────────────────────────────────────────────────────────
def test_g_malformed_json():
    print("\nG. malformed JSON")
    r = _guard(ctx_for("search_flights", '{"origin": "KHI", }'))
    check("malformed JSON is rejected", behavior(r) == "reject_content", str(r.behavior))
    check("malformed JSON reports a violation",
          (r.output_info or {}).get("violation") == "malformed_tool_arguments",
          str(r.behavior))
    check("_normalize_tool_arguments raises on malformed JSON", _raises(lambda: _normalize_tool_arguments('{"x":')))


def _raises(fn):
    try:
        fn()
        return False
    except (ValueError, TypeError, json.JSONDecodeError):
        return True


# ────────────────────────────────────────────────────────────────────────────
# H. Unexpected argument types do not bypass validation.
# ────────────────────────────────────────────────────────────────────────────
def test_h_unexpected_types():
    print("\nH. unexpected argument types are rejected")
    r = _guard(ctx_for("search_flights", {"origin": 123, "destination": "DXB", "departure_date": "2026-09-13"}))
    check("non-string origin rejected", behavior(r) == "reject_content", str(r.behavior))
    r2 = _guard(ctx_for("search_flights", {"origin": "KHI", "destination": ["DXB"], "departure_date": "2026-09-13"}))
    check("non-string destination rejected", behavior(r2) == "reject_content", str(r2.behavior))
    r3 = _guard(ctx_for("search_flights", {"origin": "KHI", "destination": "DXB", "departure_date": 2026}))
    check("non-string date rejected", behavior(r3) == "reject_content", str(r3.behavior))
    r4 = _guard(ctx_for("calculate_flight_price", {"flight_id": "abc-123456", "passengers": []}))
    check("non-numeric passengers rejected", behavior(r4) == "reject_content", str(r4.behavior))
    r5 = _guard(ctx_for("get_flight_details", {"flight_id": ["x" * 10]}))
    check("non-string flight_id rejected", behavior(r5) == "reject_content", str(r5.behavior))
    r6 = _guard(ctx_for("find_flight_by_number", {"flight_number": {"x": 1}}))
    check("non-string flight_number rejected", behavior(r6) == "reject_content", str(r6.behavior))
    r7 = _guard(ctx_for("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "min_price": "abc"}))
    check("non-numeric min_price rejected", behavior(r7) == "reject_content", str(r7.behavior))


# ────────────────────────────────────────────────────────────────────────────
# I. Existing guardrail rules still reject invalid flight tool arguments.
# ────────────────────────────────────────────────────────────────────────────
def test_i_existing_guardrail_rules():
    print("\nI. existing guardrail rules still reject invalid arguments")
    cases = [
        ("search_flights", {}),
        ("search_flights", {"origin": "", "destination": "DXB", "departure_date": "2026-09-13"}),
        ("search_flights", {"origin": "KHI", "destination": "KHI", "departure_date": "2026-09-13"}),
        ("search_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "06-09-2026"}),
        ("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "min_price": -5}),
        ("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "max_price": -5}),
        ("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "min_price": 100, "max_price": 50}),
        ("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "max_stops": -1}),
        ("calculate_flight_price", {"flight_id": "abc-123456", "passengers": 0}),
        ("check_seat_availability", {"flight_id": "abc-123456", "seats_requested": 0}),
        ("get_flight_details", {"flight_id": ""}),
        ("get_flight_details", {"flight_id": "short"}),
        ("find_flight_by_number", {"flight_number": ""}),
        ("find_flight_by_number", {"flight_number": "X"}),
    ]
    for tool_name, args in cases:
        r = _guard(ctx_for(tool_name, args))
        check(f"reject: {tool_name} {args}", behavior(r) == "reject_content", str(r.behavior))


# ────────────────────────────────────────────────────────────────────────────
# J. Valid flight tool arguments still pass.
# ────────────────────────────────────────────────────────────────────────────
def test_j_valid_arguments():
    print("\nJ. valid arguments still pass")
    good = [
        ("search_flights", {"origin": "khi", "destination": "dxb", "departure_date": "2026-09-13", "passengers": 1, "cabin_class": "economy"}),
        ("filter_flights", {"origin": "KHI", "destination": "DXB", "departure_date": "2026-09-13", "max_stops": 0, "min_price": 100, "max_price": 500}),
        ("calculate_flight_price", {"flight_id": "abc-defgh-1234", "passengers": 2}),
        ("check_seat_availability", {"flight_id": "abc-defgh-1234", "seats_requested": 2}),
        ("get_flight_details", {"flight_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}),
        ("find_flight_by_number", {"flight_number": "EK-601"}),
    ]
    for tool_name, args in good:
        r = _guard(ctx_for(tool_name, args))
        check(f"allow: {tool_name} {args}", behavior(r) == "allow", str(r.behavior))


# ────────────────────────────────────────────────────────────────────────────
# K. Integration: REAL Agents SDK path through a guarded flight tool.
#    request -> agent -> guarded tool -> guardrail -> tool -> FlightService
#              -> database -> result -> agent response
# ────────────────────────────────────────────────────────────────────────────
async def test_k_integration():
    print("\nK. Integration (real Agents SDK execution path)")
    from datetime import date, timedelta
    from config.model_config import DEFAULT_MODEL
    from database.database import init_db

    await init_db()
    # Seed data is generated for day_offsets >= 1 from today, so query tomorrow.
    departure_date = (date.today() + timedelta(days=1)).isoformat()
    probe = Agent(
        name="integration_probe",
        instructions=(
            f"Call the search_flights tool with EXACTLY these arguments: "
            f"origin='KHI', destination='DXB', departure_date='{departure_date}', "
            f"passengers=1, cabin_class='economy'. "
            f"Then reply with ONLY the tool's total_found count followed by the "
            f"id of the first flight, like: found=<n> first=<id>."
        ),
        model=DEFAULT_MODEL,
        tools=GUARDED_FLIGHT_TOOLS,
    )
    result = await Runner.run(
        probe,
        f"Search flights from KHI to DXB on {departure_date} for 1 economy passenger.",
    )
    output = result.final_output if isinstance(result.final_output, str) else str(result.final_output)
    print(f"    model output: {output[:300]}")
    check("integration: final output is non-empty", bool(output.strip()), output[:300])
    check("integration: tool call did NOT fail with 'Guardrail function must be callable'",
          "Guardrail function must be callable" not in output)
    check("integration: tool call did NOT fail with ''str' object has no attribute 'get''",
          "'str' object has no attribute 'get'" not in output)
    check("integration: flight results surfaced (found count > 0)",
          "found=" in output and any(c.isdigit() and int(c) > 0 for c in output), output[:300])
    check("integration: no internal error apology",
          "internal" not in output.lower() and "unable to process" not in output.lower(),
          output[:300])


async def main():
    print("=" * 70)
    print("PHASE 11A — GUARDED FLIGHT TOOLS & TOOL GUARDRAIL REGRESSION")
    print("=" * 70)
    test_a_no_double_wrap()
    test_b_originals_unmutated()
    test_c_guarded_shape()
    test_d_dict_args()
    test_e_json_string_args()
    test_f_empty_null()
    test_g_malformed_json()
    test_h_unexpected_types()
    test_i_existing_guardrail_rules()
    test_j_valid_arguments()
    await test_k_integration()

    print("\n" + "=" * 70)
    if failures:
        print(f"RESULT: {len(failures)} FAILED checks")
        for name in failures:
            print(f"  - {name}")
        print("=" * 70)
        sys.exit(1)
    print("RESULT: ALL CHECKS PASSED")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())