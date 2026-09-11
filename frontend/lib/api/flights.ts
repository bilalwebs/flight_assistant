import { apiFetch } from "@/lib/api/api-client";
import type {
  Flight,
  FlightFilterRequest,
  FlightSearchRequest,
  PriceBreakdown,
  SeatAvailability,
} from "@/lib/types";

/**
 * POST /api/flights/search — requires a valid bearer token.
 * `accessToken` is attached by apiFetch as `Authorization: Bearer <token>`.
 */
export function searchFlights(
  input: FlightSearchRequest,
  accessToken: string,
): Promise<Flight[]> {
  return apiFetch<Flight[]>("/api/flights/search", {
    method: "POST",
    body: input,
    token: accessToken,
  });
}

/** GET /api/flights/{flight_id} — single flight details (404 if unknown). */
export function getFlightDetails(
  flightId: string,
  accessToken: string,
): Promise<Flight> {
  return apiFetch<Flight>(`/api/flights/${encodeURIComponent(flightId)}`, {
    token: accessToken,
  });
}

/**
 * POST /api/flights/price?flight_id=...&passenger_count=... — server-side
 * price calculation. The backend is the source of truth for money.
 */
export function calculateFlightPrice(
  flightId: string,
  passengerCount: number,
  accessToken: string,
): Promise<PriceBreakdown> {
  const params = new URLSearchParams({
    flight_id: flightId,
    passenger_count: String(passengerCount),
  });
  return apiFetch<PriceBreakdown>(`/api/flights/price?${params.toString()}`, {
    method: "POST",
    token: accessToken,
  });
}

/** GET /api/flights/{flight_id}/seats — real seat availability. */
export function getSeatAvailability(
  flightId: string,
  accessToken: string,
): Promise<SeatAvailability> {
  return apiFetch<SeatAvailability>(
    `/api/flights/${encodeURIComponent(flightId)}/seats`,
    { token: accessToken },
  );
}

/** POST /api/flights/filter — advanced filter against real flights. */
export function filterFlights(
  input: FlightFilterRequest,
  accessToken: string,
): Promise<Flight[]> {
  return apiFetch<Flight[]>("/api/flights/filter", {
    method: "POST",
    body: input,
    token: accessToken,
  });
}