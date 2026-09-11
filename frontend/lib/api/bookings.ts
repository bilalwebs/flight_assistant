import { apiFetch } from "@/lib/api/api-client";
import type {
  BookingListResponse,
  BookingResponse,
  CreateBookingRequest,
} from "@/lib/types";

/**
 * GET /api/bookings/{pnr} — a single booking owned by the user.
 * The backend enforces ownership: 403 if the booking belongs to someone else,
 * 404 if the PNR is unknown.
 */
export function getBookingByPNR(
  pnr: string,
  accessToken: string,
): Promise<BookingResponse> {
  return apiFetch<BookingResponse>(
    `/api/bookings/${encodeURIComponent(pnr)}`,
    { token: accessToken },
  );
}

/**
 * GET /api/bookings — lists the authenticated user's bookings, newest first.
 * Only bookings owned by the authenticated user are ever returned.
 */
export function listMyBookings(
  accessToken: string,
): Promise<BookingListResponse> {
  return apiFetch<BookingListResponse>("/api/bookings", { token: accessToken });
}

/**
 * POST /api/bookings/{pnr}/cancel — cancels a PENDING/CONFIRMED booking
 * owned by the user and restores the released seats. The backend returns
 * 400 for state transitions that are not allowed (e.g. already cancelled).
 */
export function cancelBooking(
  pnr: string,
  accessToken: string,
): Promise<BookingResponse> {
  return apiFetch<BookingResponse>(
    `/api/bookings/${encodeURIComponent(pnr)}/cancel`,
    { method: "POST", token: accessToken },
  );
}

/**
 * POST /api/bookings — creates a booking as the authenticated user.
 * The backend validates the flight, seats, passenger data and calculates the
 * authoritative price server-side. Returns a PENDING booking with its PNR.
 */
export function createBooking(
  input: CreateBookingRequest,
  accessToken: string,
): Promise<BookingResponse> {
  return apiFetch<BookingResponse>("/api/bookings", {
    method: "POST",
    body: input,
    token: accessToken,
  });
}

/**
 * POST /api/bookings/{pnr}/confirm — confirms a PENDING booking
 * (PENDING → CONFIRMED). Ownership is enforced by the backend.
 */
export function confirmBooking(
  pnr: string,
  accessToken: string,
): Promise<BookingResponse> {
  return apiFetch<BookingResponse>(
    `/api/bookings/${encodeURIComponent(pnr)}/confirm`,
    { method: "POST", token: accessToken },
  );
}

