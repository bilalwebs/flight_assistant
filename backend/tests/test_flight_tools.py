"""
Phase 4 — Flight Tools test suite.

Every tool is invoked through the REAL OpenAI Agents SDK mechanism
(FunctionTool.on_invoke_tool with a ToolContext + JSON arguments),
exactly as an Agent would call it during a run. Nothing is called directly.
"""
import asyncio
import json
import uuid

from datetime import datetime, timedelta
from agents.tool_context import ToolContext

from tools.flight_tools import (
    search_flights, get_flight_details, filter_flights,
    compare_flights, calculate_flight_price, check_seat_availability,
)

PASS = "PASS"
FAIL = "FAIL"


async def invoke(tool, **kwargs) -> dict:
    """Invoke a FunctionTool exactly the way the Agents SDK does at runtime."""
    args = json.dumps(kwargs)
    ctx = ToolContext(
        context=None,
        tool_name=tool.name,
        tool_call_id=str(uuid.uuid4()),
        tool_arguments=args,
    )
    return await tool.on_invoke_tool(ctx, args)


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


async def run_tests() -> None:
    test_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    results: list[bool] = []

    print("=" * 60)
    print("PHASE 4 — FLIGHT TOOLS (via Agents SDK on_invoke_tool)")
    print("=" * 60)

    # 1. search_flights KHI -> DXB
    print("\n[1] search_flights  KHI -> DXB")
    r = await invoke(search_flights, origin="KHI", destination="DXB", departure_date=test_date)
    results.append(check("returns flights", r.get("total_found", 0) > 0, f"{r.get('total_found')} found"))

    flights = r.get("flights", [])
    sample_id = flights[0]["id"] if flights else None
    second_id = flights[1]["id"] if len(flights) > 1 else None

    # 2. search_flights KHI -> IST
    print("\n[2] search_flights  KHI -> IST")
    r = await invoke(search_flights, origin="KHI", destination="IST", departure_date=test_date)
    results.append(check("returns Istanbul flights", r.get("total_found", 0) > 0, f"{r.get('total_found')} found"))

    # 3. no-result route
    print("\n[3] search_flights  KHI -> LAX (no route)")
    r = await invoke(search_flights, origin="KHI", destination="LAX", departure_date=test_date)
    results.append(check("gracefully returns zero", r.get("total_found") == 0, r.get("message", "")))

    # 4. get_flight_details
    print("\n[4] get_flight_details")
    r = await invoke(get_flight_details, flight_id=sample_id)
    results.append(check("retrieves correct flight", r.get("id") == sample_id, r.get("flight_number", "")))

    # 5. filter direct flights
    print("\n[5] filter_flights  max_stops=0")
    r = await invoke(filter_flights, origin="KHI", destination="DXB", departure_date=test_date, max_stops=0)
    results.append(check("returns direct flights", r.get("count", 0) > 0, f"{r.get('count')} direct"))

    # 6. filter by price
    print("\n[6] filter_flights  max_price=250")
    r = await invoke(filter_flights, origin="KHI", destination="DXB", departure_date=test_date, max_price=250)
    all_cheap = all(f["base_price"] <= 250 for f in r.get("flights", []))
    results.append(check("all within budget", r.get("count", 0) > 0 and all_cheap, f"{r.get('count')} <= $250"))

    # 7. filter by time-of-day
    print("\n[7] filter_flights  time_of_day=morning")
    r = await invoke(filter_flights, origin="KHI", destination="DXB", departure_date=test_date, time_of_day="morning")
    results.append(check("returns morning flights", r.get("count", 0) > 0, f"{r.get('count')} morning"))

    # 8. compare flights
    print("\n[8] compare_flights")
    r = await invoke(compare_flights, flight_ids=[sample_id, second_id])
    comp = r.get("comparison", [])
    sorted_ok = comp == sorted(comp, key=lambda x: (x["price"], x["duration"]))
    results.append(check("returns sorted comparison", r.get("count", 0) == 2 and sorted_ok, f"{r.get('count')} compared"))

    # 9. calculate price for multiple passengers
    print("\n[9] calculate_flight_price  passengers=3")
    r = await invoke(calculate_flight_price, flight_id=sample_id, passengers=3)
    expected = round(r.get("total_per_person", 0) * 3, 2)
    results.append(check("grand_total = per_person x 3",
                         round(r.get("grand_total", -1), 2) == expected,
                         f"${r.get('grand_total')}"))

    # 10. check seat availability
    print("\n[10] check_seat_availability  seats=5")
    r = await invoke(check_seat_availability, flight_id=sample_id, requested_seats=5)
    results.append(check("reports availability", r.get("available") is True, f"remaining {r.get('remaining_seats')}"))

    print("\n[10b] check_seat_availability  seats=9999 (oversell)")
    r = await invoke(check_seat_availability, flight_id=sample_id, requested_seats=9999)
    results.append(check("rejects oversell", r.get("available") is False))

    # 11. invalid flight ID
    print("\n[11] get_flight_details  invalid ID")
    r = await invoke(get_flight_details, flight_id="does-not-exist")
    results.append(check("clean not-found error", r.get("success") is False and "error" in r, r.get("error", "")))

    # 12. invalid input (bad date + bad cabin)
    print("\n[12] search_flights  invalid date format")
    r = await invoke(search_flights, origin="KHI", destination="DXB", departure_date="06-09-2026")
    results.append(check("clean invalid-input error", r.get("success") is False and "error" in r, r.get("error", "")))

    print("\n[12b] search_flights  invalid cabin class")
    r = await invoke(search_flights, origin="KHI", destination="DXB", departure_date=test_date, cabin_class="spaceship")
    results.append(check("clean invalid-cabin error", r.get("success") is False and "error" in r, r.get("error", "")))

    # 13. calculate price with invalid passenger count
    print("\n[13] calculate_flight_price  passengers=0")
    r = await invoke(calculate_flight_price, flight_id=sample_id, passengers=0)
    results.append(check("rejects zero passengers", r.get("success") is False and "error" in r, r.get("error", "")))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for x in results if x)
    total = len(results)
    print(f"RESULT: {passed}/{total} checks passed")
    print("=" * 60)
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
