"use client";

import type { BookingResponse, Flight } from "@/lib/types";
import { formatFullDate, formatPrice, formatTime } from "@/lib/utils/date";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface BookingConfirmationProps {
  booking: BookingResponse;
  flight: Flight;
  /** "pending" = awaiting explicit confirmation; "confirmed" = finalized. */
  status: "pending" | "confirmed";
  confirming?: boolean;
  confirmError?: string | null;
  onConfirm?: () => void;
}

export function BookingConfirmation({
  booking,
  flight,
  status,
  confirming = false,
  confirmError = null,
  onConfirm,
}: BookingConfirmationProps) {
  const confirmed = status === "confirmed";

  return (
    <div
      className="mx-auto w-full max-w-2xl"
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        className={
          "rounded-2xl border bg-white p-6 shadow-card " +
          (confirmed ? "border-emerald-200" : "border-amber-200")
        }
      >
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span
              className={
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-full " +
                (confirmed ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700")
              }
            >
              {confirmed ? (
                <svg
                  aria-hidden="true"
                  className="h-6 w-6"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              ) : (
                <svg
                  aria-hidden="true"
                  className="h-6 w-6"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              )}
            </span>
            <div>
              <h1 className="font-heading text-xl font-semibold tracking-tight text-foreground">
                {confirmed ? "Booking Confirmed" : "Booking Pending"}
              </h1>
              <div className="mt-1">
                {confirmed ? (
                  <Badge variant="success">CONFIRMED</Badge>
                ) : (
                  <Badge variant="warning">PENDING</Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        <dl
          className={
            "mt-6 divide-y divide-slate-100 rounded-xl border border-slate-100 px-4 " +
            (confirmed ? "bg-emerald-50/40" : "bg-amber-50/40")
          }
        >
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">PNR</dt>
            <dd className="font-mono text-sm font-semibold tracking-wider text-foreground">
              {booking.pnr}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Flight</dt>
            <dd className="text-sm font-medium text-foreground">
              {flight.airline_code} {flight.flight_number}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Route</dt>
            <dd className="text-sm text-slate-700">
              {flight.origin} → {flight.destination}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Departure</dt>
            <dd className="text-sm text-slate-700">
              {formatFullDate(flight.departure_time)} · {formatTime(flight.departure_time)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Passengers</dt>
            <dd className="text-sm text-slate-700">{booking.passenger_count}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Total</dt>
            <dd className="font-heading text-lg font-semibold tracking-tight text-foreground">
              {formatPrice(booking.total_amount)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Contact email</dt>
            <dd className="text-sm text-slate-700">{booking.contact_email}</dd>
          </div>
        </dl>

        {confirmError ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {confirmError}
          </p>
        ) : null}

        <div className="mt-6">
          {confirmed ? (
            <Button variant="primary" size="lg" fullWidth href="/bookings">
              View My Bookings
            </Button>
          ) : (
            <Button
              variant="primary"
              size="lg"
              fullWidth
              loading={confirming}
              disabled={confirming || !onConfirm}
              onClick={onConfirm}
              aria-label="Confirm booking"
            >
              {confirming ? "Confirming booking..." : "Confirm Booking"}
            </Button>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-slate-500">
          {confirmed
            ? "Your booking is confirmed. A confirmation was saved for this PNR."
            : "Your booking is reserved but not yet confirmed. Confirm to finalize — no payment is required in this phase."}
        </p>
      </div>
    </div>
  );
}