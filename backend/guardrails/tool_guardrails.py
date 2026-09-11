"""
Phase 10 — Tool Guardrails (Agents SDK).

Purpose: Validate tool invocation arguments BEFORE execution, catching obviously
invalid inputs (negative prices, empty origins, origin==destination, nonsensical
passenger counts) before they reach FlightService or the database.

IMPORTANT: This is an ADDITIONAL safety layer. FlightService remains responsible
for business rules and database validation. Tool guardrails prevent unnecessary
service calls when the arguments are trivially invalid.

Architecture:
    Agent
     ↓
    Tool Guardrail (validates args)
     ↓
    Flight Tool
     ↓
    FlightService (business rules)
     ↓
    Database

The guardrail does NOT replace service validation; it short-circuits obviously
bad calls.
"""
from agents.tool_guardrails import (
    ToolGuardrailFunctionOutput,
    ToolInputGuardrailData,
    tool_input_guardrail,
)


@tool_input_guardrail(name="flight_tool_input_validation")
def validate_flight_tool_inputs(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
    """Validate flight tool arguments before execution.

    Checks depend on the tool being called (identified via data.context.tool_name).

    Returns:
        ToolGuardrailFunctionOutput with behavior:
          - allow: arguments are valid, proceed normally
          - reject_content: arguments are invalid, return error message to model
          - raise_exception: (reserved for critical failures)
    """
    tool_name = data.context.tool_name
    args = data.context.tool_arguments or {}

    # ──────────────────────────────────────────────────────────────────────────
    # search_flights / filter_flights — route and date validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name in ("search_flights", "filter_flights"):
        origin = args.get("origin", "").strip().upper()
        destination = args.get("destination", "").strip().upper()

        # Origin must be present.
        if not origin:
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight search: origin airport code is required.",
                output_info={"tool": tool_name, "violation": "missing_origin"},
            )

        # Destination must be present.
        if not destination:
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight search: destination airport code is required.",
                output_info={"tool": tool_name, "violation": "missing_destination"},
            )

        # Origin must not equal destination.
        if origin == destination:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight search: origin and destination are the same ({origin}). Please provide two different airports.",
                output_info={"tool": tool_name, "violation": "origin_equals_destination", "value": origin},
            )

        # Date format check (if provided) — expect YYYY-MM-DD. The service will
        # do the full parse, but we can catch obvious typos like "06-09-2026".
        date_str = args.get("date")
        if date_str:
            parts = str(date_str).split("-")
            if len(parts) != 3:
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid date format: {date_str}. Expected YYYY-MM-DD.",
                    output_info={"tool": tool_name, "violation": "invalid_date_format", "value": date_str},
                )
            # Check year is 4 digits, month/day are 2 digits (basic sanity).
            year, month, day = parts
            if len(year) != 4 or len(month) != 2 or len(day) != 2:
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid date format: {date_str}. Expected YYYY-MM-DD.",
                    output_info={"tool": tool_name, "violation": "invalid_date_format", "value": date_str},
                )

    # ──────────────────────────────────────────────────────────────────────────
    # filter_flights — price and stops validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name == "filter_flights":
        min_price = args.get("min_price")
        max_price = args.get("max_price")
        max_stops = args.get("max_stops")

        # Prices must be non-negative.
        if min_price is not None:
            try:
                min_val = float(min_price)
                if min_val < 0:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid filter: min_price cannot be negative (got {min_price}).",
                        output_info={"tool": tool_name, "violation": "negative_min_price", "value": min_price},
                    )
            except (ValueError, TypeError):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid filter: min_price must be a number (got {min_price}).",
                    output_info={"tool": tool_name, "violation": "invalid_min_price", "value": min_price},
                )

        if max_price is not None:
            try:
                max_val = float(max_price)
                if max_val < 0:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid filter: max_price cannot be negative (got {max_price}).",
                        output_info={"tool": tool_name, "violation": "negative_max_price", "value": max_price},
                    )
            except (ValueError, TypeError):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid filter: max_price must be a number (got {max_price}).",
                    output_info={"tool": tool_name, "violation": "invalid_max_price", "value": max_price},
                )

        # min_price must not exceed max_price.
        if min_price is not None and max_price is not None:
            try:
                if float(min_price) > float(max_price):
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid filter: min_price ({min_price}) cannot exceed max_price ({max_price}).",
                        output_info={"tool": tool_name, "violation": "min_exceeds_max_price", "min": min_price, "max": max_price},
                    )
            except (ValueError, TypeError):
                pass  # Already caught above.

        # max_stops must not be negative.
        if max_stops is not None:
            try:
                stops_val = int(max_stops)
                if stops_val < 0:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid filter: max_stops cannot be negative (got {max_stops}).",
                        output_info={"tool": tool_name, "violation": "negative_max_stops", "value": max_stops},
                    )
            except (ValueError, TypeError):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid filter: max_stops must be an integer (got {max_stops}).",
                    output_info={"tool": tool_name, "violation": "invalid_max_stops", "value": max_stops},
                )

    # ──────────────────────────────────────────────────────────────────────────
    # calculate_flight_price — passenger count validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name == "calculate_flight_price":
        passengers = args.get("passengers")
        if passengers is not None:
            try:
                p_val = int(passengers)
                if p_val <= 0:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid passenger count: must be at least 1 (got {passengers}).",
                        output_info={"tool": tool_name, "violation": "non_positive_passengers", "value": passengers},
                    )
                # Sanity upper bound (e.g., commercial flights rarely exceed 500-600 seats).
                if p_val > 1000:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid passenger count: {passengers} exceeds reasonable limit.",
                        output_info={"tool": tool_name, "violation": "excessive_passengers", "value": passengers},
                    )
            except (ValueError, TypeError):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid passenger count: must be an integer (got {passengers}).",
                    output_info={"tool": tool_name, "violation": "invalid_passengers", "value": passengers},
                )

    # ──────────────────────────────────────────────────────────────────────────
    # check_seat_availability — seats requested validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name == "check_seat_availability":
        seats = args.get("seats_requested")
        if seats is not None:
            try:
                s_val = int(seats)
                if s_val <= 0:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid seat check: seats_requested must be at least 1 (got {seats}).",
                        output_info={"tool": tool_name, "violation": "non_positive_seats", "value": seats},
                    )
                if s_val > 1000:
                    return ToolGuardrailFunctionOutput.reject_content(
                        message=f"Invalid seat check: {seats} exceeds reasonable limit.",
                        output_info={"tool": tool_name, "violation": "excessive_seats", "value": seats},
                    )
            except (ValueError, TypeError):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid seat check: seats_requested must be an integer (got {seats}).",
                    output_info={"tool": tool_name, "violation": "invalid_seats", "value": seats},
                )

    # ──────────────────────────────────────────────────────────────────────────
    # get_flight_details / find_flight_by_number — ID/number presence validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name == "get_flight_details":
        flight_id = args.get("flight_id", "").strip()
        if not flight_id:
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight details request: flight_id is required.",
                output_info={"tool": tool_name, "violation": "missing_flight_id"},
            )
        # Basic length sanity (UUIDs are 36 chars with hyphens; our DB uses them).
        if len(flight_id) < 8:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight_id: too short ({flight_id}).",
                output_info={"tool": tool_name, "violation": "flight_id_too_short", "value": flight_id},
            )

    if tool_name == "find_flight_by_number":
        flight_number = args.get("flight_number", "").strip()
        if not flight_number:
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight lookup: flight_number is required.",
                output_info={"tool": tool_name, "violation": "missing_flight_number"},
            )
        # Sanity: flight numbers are typically 2-10 characters (e.g., EK-601, PK-201).
        if len(flight_number) < 2 or len(flight_number) > 20:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight_number: unusual length ({flight_number}).",
                output_info={"tool": tool_name, "violation": "flight_number_unusual_length", "value": flight_number},
            )

    # All checks passed — allow normal tool execution.
    return ToolGuardrailFunctionOutput.allow(
        output_info={"tool": tool_name, "status": "valid"}
    )
