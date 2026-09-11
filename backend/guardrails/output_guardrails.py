"""
Phase 10 — Output Guardrails (Agents SDK).

Purpose: Validate that the final agent output respects the application's data
contracts and invariants, particularly for structured FlightSearchResponse outputs.

CRITICAL: This guardrail validates OUTPUT INVARIANTS, not data correctness.
Flight data correctness is the responsibility of FlightService + database + tool
grounding rules. The output guardrail checks that the STRUCTURE is coherent:
  * total_results == len(flights) (count matches)
  * recommendation IDs (cheapest/fastest) are null when no flights, or refer to
    returned flights when populated
  * no obviously malformed records (negative prices, empty required fields)

DO NOT query the database from the output guardrail. The guardrail is NOT
reimplementing FlightService — it is a final sanity check on the output contract.
"""
from agents import Agent, RunContextWrapper
from agents.guardrail import GuardrailFunctionOutput, output_guardrail


@output_guardrail(name="structured_output_validation")
def validate_output_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    agent_output,
) -> GuardrailFunctionOutput:
    """Validate structured flight outputs for basic invariant violations.

    Checks:
      * FlightSearchResponse: total_results == len(flights), recommendation IDs
        are valid, prices are non-negative.
      * FlightDetailsResponse: success/flight consistency, non-negative price.

    Returns:
        GuardrailFunctionOutput with tripwire_triggered=True if a violation is detected.
    """
    # Defer imports to avoid circular dependencies at module load time.
    from models.responses import FlightSearchResponse, FlightDetailsResponse

    checks_performed = []

    # Only validate structured outputs; plain text responses (from Travel Assistant,
    # or the Orchestrator's composed prose) pass through unchecked.
    if isinstance(agent_output, FlightSearchResponse):
        resp = agent_output
        checks_performed.append("FlightSearchResponse")

        # Invariant 1: total_results must match the actual number of flights returned.
        if resp.total_results != len(resp.flights):
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "total_results_mismatch",
                    "total_results": resp.total_results,
                    "actual_count": len(resp.flights),
                },
                tripwire_triggered=True,
            )

        flight_ids = {f.flight_id for f in resp.flights}

        # Invariant 2: If flights are empty, recommendation IDs MUST be None.
        if len(resp.flights) == 0:
            if resp.cheapest_flight_id is not None or resp.fastest_flight_id is not None:
                return GuardrailFunctionOutput(
                    output_info={
                        "checks": checks_performed,
                        "violation": "recommendations_present_but_no_flights",
                        "cheapest": resp.cheapest_flight_id,
                        "fastest": resp.fastest_flight_id,
                    },
                    tripwire_triggered=True,
                )

        # Invariant 3: If recommendation IDs are populated, they must refer to
        # one of the returned flights.
        if resp.cheapest_flight_id is not None and resp.cheapest_flight_id not in flight_ids:
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "cheapest_flight_id_not_in_results",
                    "cheapest_id": resp.cheapest_flight_id,
                    "returned_ids": list(flight_ids)[:10],
                },
                tripwire_triggered=True,
            )

        if resp.fastest_flight_id is not None and resp.fastest_flight_id not in flight_ids:
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "fastest_flight_id_not_in_results",
                    "fastest_id": resp.fastest_flight_id,
                    "returned_ids": list(flight_ids)[:10],
                },
                tripwire_triggered=True,
            )

        # Invariant 4: Prices must be non-negative (a negative price is malformed).
        for flight in resp.flights:
            if flight.price < 0:
                return GuardrailFunctionOutput(
                    output_info={
                        "checks": checks_performed,
                        "violation": "negative_price",
                        "flight_id": flight.flight_id,
                        "price": flight.price,
                    },
                    tripwire_triggered=True,
                )

    elif isinstance(agent_output, FlightDetailsResponse):
        resp = agent_output
        checks_performed.append("FlightDetailsResponse")

        # Invariant: If success is True, flight MUST be populated. If success is
        # False, flight MUST be None.
        if resp.success and resp.flight is None:
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "success_true_but_flight_none",
                },
                tripwire_triggered=True,
            )

        if not resp.success and resp.flight is not None:
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "success_false_but_flight_present",
                },
                tripwire_triggered=True,
            )

        # If flight is populated, price must be non-negative.
        if resp.flight is not None and resp.flight.price < 0:
            return GuardrailFunctionOutput(
                output_info={
                    "checks": checks_performed,
                    "violation": "negative_price",
                    "flight_id": resp.flight.flight_id,
                    "price": resp.flight.price,
                },
                tripwire_triggered=True,
            )

    # No violations detected — output is valid.
    return GuardrailFunctionOutput(
        output_info={"checks": checks_performed, "status": "valid"}, tripwire_triggered=False
    )

