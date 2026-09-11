"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ApiError } from "@/lib/api/api-client";
import { cancelBooking, getBookingByPNR } from "@/lib/api/bookings";
import { getFlightDetails } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import type { BookingResponse, Flight } from "@/lib/types";
import {
  formatCabin,
  formatDuration,
  formatFullDate,
  formatPassengers,
  formatPrice,
  formatStops,
  formatTime,
} from "@/lib/utils/date";

import { BookingStatusBadge } from "@/components/bookings/BookingStatusBadge";
import { CancelBookingDialog } from "@/components/bookings/CancelBookingDialog";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/LoadingSkeleton";

interface BookingDetailsProps {
  pnr: string;
}

export function BookingDetails({ pnr }: BookingDetailsProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const [booking, setBooking] = useState<BookingResponse | null>(null);
  const [flight, setFlight] = useState<Flight | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const fetched = await getBookingByPNR(pnr, accessToken);
      setBooking(fetched);
      try {
        const fetchedFlight = await getFlightDetails(fetched.flight_id, accessToken);
        setFlight(fetchedFlight);
      } catch {
        // Flight unavailable — show booking without flight details.
      }
      setLoading(false);
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.status === 401) {
          handleUnauthorized();
          return;
        }
        setError(caught);
      } else {
        setError(
          new ApiError("Something went wrong. Please try again.", {
            status: 0,
            code: "unknown",
          }),
        );
      }
      setLoading(false);
    }
  }, [pnr, accessToken, handleUnauthorized]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const fetched = await getBookingByPNR(pnr, accessToken ?? "");
        if (cancelled) return;
        setBooking(fetched);
        try {
          const fetchedFlight = await getFlightDetails(fetched.flight_id, accessToken ?? "");
          if (!cancelled) setFlight(fetchedFlight);
        } catch {
          // Flight unavailable — show booking without flight details.
        }
        if (!cancelled) setLoading(false);
      } catch (caught) {
        if (cancelled) return;
        if (caught instanceof ApiError) {
          if (caught.status === 401) {
            handleUnauthorized();
            return;
          }
          setError(caught);
        } else {
          setError(
            new ApiError("Something went wrong. Please try again.", {
              status: 0,
              code: "unknown",
            }),
          );
        }
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pnr, accessToken, handleUnauthorized]);

  async function handleCancel() {
    if (!booking || !accessToken) return;
    setSubmitting(true);
    setCancelError(null);
    try {
      const updated = await cancelBooking(booking.pnr, accessToken);
      setBooking(updated);
      setDialogOpen(false);
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.message
          : "Cancellation failed. Please try again.";
      setCancelError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading && !error) {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-5">
        <Skeleton className="h-9 w-52 rounded-lg" />
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
      </div>
    );
  }

  if (error) {
    const title =
      error.status === 404
        ? "Booking not found"
        : error.status === 403
          ? "Access denied"
          : "Something went wrong";
    const message =
      error.status === 403
        ? "You don't have permission to view this booking."
        : error.message;
    return (
      <div className="mx-auto w-full max-w-2xl">
        <ErrorState
          title={title}
          message={message}
          onRetry={error.status !== 403 && error.status !== 404 ? () => void load() : undefined}
        />
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <ErrorState title="Booking not found" message="This booking does not exist." />
      </div>
    );
  }

  const canCancel = booking.status === "pending" || booking.status === "confirmed";

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <Link
        href="/bookings"
        className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
        aria-label="Back to My Bookings"
      >
        ← My Bookings
      </Link>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-bold tracking-wider text-foreground">
              {booking.pnr}
            </h1>
            <BookingStatusBadge status={booking.status} />
          </div>

          {canCancel ? (
            <Button
              variant="danger"
              size="sm"
              disabled={submitting}
              onClick={() => {
                setCancelError(null);
                setDialogOpen(true);
              }}
              aria-label="Cancel booking"
            >
              Cancel booking
            </Button>
          ) : null}
        </div>

        {flight ? (
          <dl className="mt-6 divide-y divide-slate-100 rounded-xl border border-slate-100 px-4">
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Flight</dt>
              <dd className="text-sm font-medium text-foreground">
                {flight.airline_code} {flight.flight_number}
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Route</dt>
              <dd className="text-sm text-foreground">
                {flight.origin} → {flight.destination}
                <span className="ml-2 text-slate-500">
                  {flight.origin_city} → {flight.destination_city}
                </span>
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Departure</dt>
              <dd className="text-sm text-foreground">
                {formatFullDate(flight.departure_time)} · {formatTime(flight.departure_time)}
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Arrival</dt>
              <dd className="text-sm text-foreground">
                {formatFullDate(flight.arrival_time)} · {formatTime(flight.arrival_time)}
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Duration</dt>
              <dd className="text-sm text-foreground">
                {formatDuration(flight.duration_minutes)} · {formatStops(flight.stops)}
              </dd>
            </div>
          </dl>
        ) : null}

        <dl className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-100 px-4">
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Cabin</dt>
            <dd className="text-sm font-medium capitalize text-foreground">
              {formatCabin(booking.cabin_class)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Passengers</dt>
            <dd className="text-sm text-foreground">
              {formatPassengers(booking.passenger_count)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Base fare</dt>
            <dd className="text-sm text-foreground">{formatPrice(booking.base_amount)}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Tax</dt>
            <dd className="text-sm text-foreground">{formatPrice(booking.tax_amount)}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Total</dt>
            <dd className="font-heading text-lg font-semibold text-foreground">
              {formatPrice(booking.total_amount)}
            </dd>
          </div>
        </dl>

        <dl className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-100 px-4">
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-slate-600">Contact email</dt>
            <dd className="text-sm text-foreground">{booking.contact_email}</dd>
          </div>
          {booking.contact_phone ? (
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Phone</dt>
              <dd className="text-sm text-foreground">{booking.contact_phone}</dd>
            </div>
          ) : null}
          {booking.created_at ? (
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-slate-600">Created</dt>
              <dd className="text-sm text-foreground">{formatFullDate(booking.created_at)}</dd>
            </div>
          ) : null}
        </dl>
      </div>

      <CancelBookingDialog
        open={dialogOpen}
        booking={booking}
        submitting={submitting}
        errorMessage={cancelError}
        onConfirm={handleCancel}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  );
}