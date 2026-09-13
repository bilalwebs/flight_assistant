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
import json

from agents.tool_guardrails import (
    ToolGuardrailFunctionOutput,
    ToolInputGuardrailData,
    tool_input_guardrail,
)


def _normalize_tool_arguments(tool_arguments):
    """Return tool arguments as a dict.

    Depending on the Agents SDK version, ``data.context.tool_arguments`` is
    delivered either as an already-parsed dict or as a raw JSON string. Accept
    both forms and reject anything that cannot be decoded so that guardrail
    validation is never silently bypassed.

    Returns:
        dict: the tool arguments.

    Raises:
        ValueError/TypeError: when the value is malformed or of an unexpected
            type (which the caller converts into a guardrail rejection).
    """
    if tool_arguments is None:
        return {}
    if isinstance(tool_arguments, dict):
        return tool_arguments
    if isinstance(tool_arguments, str):
        text = tool_arguments.strip()
        if not text:
            return {}
        decoded = json.loads(text)
        if isinstance(decoded, dict):
            return decoded
        raise TypeError("tool arguments did not decode to a JSON object")
    raise TypeError(f"unexpected tool arguments type: {type(tool_arguments).__name__}")


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
    try:
        args = _normalize_tool_arguments(data.context.tool_arguments)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return ToolGuardrailFunctionOutput.reject_content(
            message=f"Invalid tool arguments: {e}",
            output_info={
                "tool": tool_name,
                "violation": "malformed_tool_arguments",
                "raw": str(data.context.tool_arguments)[:200],
            },
        )

    # ──────────────────────────────────────────────────────────────────────────
    # search_flights / filter_flights — route and date validation
    # ──────────────────────────────────────────────────────────────────────────
    if tool_name in ("search_flights", "filter_flights"):
        origin = args.get("origin")
        destination = args.get("destination")

        # Origin must be present and a non-empty string.
        if not isinstance(origin, str) or not origin.strip():
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight search: origin airport code is required.",
                output_info={"tool": tool_name, "violation": "missing_origin"},
            )

        # Destination must be present and a non-empty string.
        if not isinstance(destination, str) or not destination.strip():
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight search: destination airport code is required.",
                output_info={"tool": tool_name, "violation": "missing_destination"},
            )

        origin = origin.strip().upper()
        destination = destination.strip().upper()

        # Origin must not equal destination.
        if origin == destination:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight search: origin and destination are the same ({origin}). Please provide two different airports.",
                output_info={"tool": tool_name, "violation": "origin_equals_destination", "value": origin},
            )

        # Date format check (if provided) — expect YYYY-MM-DD. The service will
        # do the full parse, but we can catch obvious typos like "06-09-2026".
        # Both search and filter tools declare the parameter as `departure_date`;
        # `date` is accepted as a fallback key for older callers.
        date_str = args.get("departure_date", args.get("date"))
        if date_str is not None:
            # Reject non-string date values so unexpected types cannot reach the service.
            if not isinstance(date_str, str):
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"Invalid date format: expected a YYYY-MM-DD string, got {type(date_str).__name__}.",
                    output_info={"tool": tool_name, "violation": "invalid_date_format", "value": str(date_str)},
                )
            parts = date_str.split("-")
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
        flight_id = args.get("flight_id")
        if not isinstance(flight_id, str) or not flight_id.strip():
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight details request: flight_id is required.",
                output_info={"tool": tool_name, "violation": "missing_flight_id"},
            )
        # Basic length sanity (UUIDs are 36 chars with hyphens; our DB uses them).
        if len(flight_id.strip()) < 8:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight_id: too short ({flight_id}).",
                output_info={"tool": tool_name, "violation": "flight_id_too_short", "value": flight_id},
            )

    if tool_name == "find_flight_by_number":
        flight_number = args.get("flight_number")
        if not isinstance(flight_number, str) or not flight_number.strip():
            return ToolGuardrailFunctionOutput.reject_content(
                message="Invalid flight lookup: flight_number is required.",
                output_info={"tool": tool_name, "violation": "missing_flight_number"},
            )
        # Sanity: flight numbers are typically 2-10 characters (e.g., EK-601, PK-201).
        stripped_number = flight_number.strip()
        if len(stripped_number) < 2 or len(stripped_number) > 20:
            return ToolGuardrailFunctionOutput.reject_content(
                message=f"Invalid flight_number: unusual length ({flight_number}).",
                output_info={"tool": tool_name, "violation": "flight_number_unusual_length", "value": flight_number},
            )

    # All checks passed — allow normal tool execution.
    return ToolGuardrailFunctionOutput.allow(
        output_info={"tool": tool_name, "status": "valid"}
    )
