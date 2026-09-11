"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { getFlightDetails } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import { useSearch } from "@/lib/search/search-context";
import type { Flight } from "@/lib/types";
import {
  formatCabin,
  formatDuration,
  formatFullDate,
  formatStops,
  formatTime,
} from "@/lib/utils/date";

import { PriceBreakdown } from "@/components/flights/PriceBreakdown";
import { SeatAvailability } from "@/components/flights/SeatAvailability";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/feedback/LoadingSkeleton";

type LoadStatus =
  | { kind: "loading" }
  | { kind: "error"; errorKind: "not_found" | "forbidden" | "network" | "server" }
  | { kind: "done" };

function classifyError(error: unknown): LoadStatus {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "not_found":
        return { kind: "error", errorKind: "not_found" };
      case "forbidden":
        return { kind: "error", errorKind: "forbidden" };
      case "network":
        return { kind: "error", errorKind: "network" };
      default:
        return { kind: "error", errorKind: "server" };
    }
  }
  return { kind: "error", errorKind: "server" };
}

function DetailsSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading flight details">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <div className="flex items-center gap-3">
          <Skeleton className="h-12 w-12 rounded-xl" />
          <div className="flex flex-col gap-2">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <div className="flex items-center justify-between gap-4">
          <Skeleton className="h-12 w-24" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-12 w-24" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-4 h-8 w-24" />
          <Skeleton className="mt-3 h-2 w-full" />
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <Skeleton className="h-5 w-32" />
          <div className="mt-4 space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
      </div>
    </div>
  );
}

interface FlightDetailsProps {
  flightId: string;
}

export function FlightDetails({ flightId }: FlightDetailsProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const { searchParams } = useSearch();
  const [flight, setFlight] = useState<Flight | null>(null);
  const [status, setStatus] = useState<LoadStatus>({ kind: "loading" });

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const details = await getFlightDetails(flightId, accessToken ?? "");
      setFlight(details);
      setStatus({ kind: "done" });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return;
      }
      setStatus(classifyError(error));
    }
  }, [flightId, accessToken, handleUnauthorized]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const details = await getFlightDetails(flightId, accessToken ?? "");
        if (!cancelled) {
          setFlight(details);
          setStatus({ kind: "done" });
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 401) {
            handleUnauthorized();
            return;
          }
          setStatus(classifyError(error));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [flightId, accessToken, handleUnauthorized]);

  const backButton = (
    <Button
      variant="ghost"
      size="sm"
      href="/flights/search"
      className="mb-4 -ml-2 text-slate-600"
    >
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m12 19-7-7 7-7" />
        <path d="M19 12H5" />
      </svg>
      Back to search results
    </Button>
  );

  let content: React.ReactNode = null;

  if (status.kind === "loading") {
    content = <DetailsSkeleton />;
  } else if (status.kind === "error") {
    if (status.errorKind === "not_found") {
      content = (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <h2 className="font-heading text-lg font-semibold text-foreground">
            Flight not found
          </h2>
          <p className="max-w-sm text-sm text-slate-600">
            This flight may have been removed or the link is incorrect.
          </p>
          <Button variant="outline" size="sm" href="/flights/search" className="mt-1">
            Back to Search
          </Button>
        </div>
      );
    } else {
      const message =
        status.errorKind === "forbidden"
          ? "Your account doesn't have access to this flight."
          : "We couldn't load the flight details. Please try again.";
      content = (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-card">
          <h2 className="font-heading text-lg font-semibold text-foreground">
            Unable to load flight details.
          </h2>
          <p className="max-w-sm text-sm text-slate-600">{message}</p>
          <Button variant="outline" size="sm" onClick={() => void load()} className="mt-1">
            Retry
          </Button>
        </div>
      );
    }
  } else if (flight) {
    content = (
      <div className="space-y-4">
        <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-sm font-semibold text-primary-700">
                {flight.airline_code}
              </span>
              <div>
                <p className="font-heading text-lg font-semibold tracking-tight text-slate-900">
                  {flight.airline}
                </p>
                <p className="text-sm text-slate-500">
                  Flight {flight.flight_number}
                </p>
              </div>
            </div>
            <div className="flex flex-col items-start gap-3 sm:items-end">
              <div className="flex items-center gap-1.5">
                <Badge variant="info">{formatCabin(flight.cabin_class)}</Badge>
                <Badge variant={flight.stops === 0 ? "success" : "default"}>
                  {formatStops(flight.stops)}
                </Badge>
              </div>
              {flight.available_seats > 0 ? (
                <Button size="sm" href={`/bookings/new/${flight.id}`} className="w-full sm:w-auto">
                  Book This Flight
                </Button>
              ) : (
                <Button size="sm" disabled className="w-full sm:w-auto" aria-disabled="true">
                  Sold out
                </Button>
              )}
            </div>
          </div>
        </header>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card sm:p-6"
          aria-label="Route and schedule"
        >
          <div className="grid grid-cols-1 items-center gap-5 sm:grid-cols-[1fr_auto_1fr] sm:gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Departure
              </p>
              <p className="mt-1 font-heading text-2xl font-semibold tracking-tight text-foreground">
                {flight.origin_city}
              </p>
              <p className="text-sm text-slate-600">{flight.origin}</p>
              <p className="mt-2 text-sm text-slate-700">
                {formatFullDate(flight.departure_time)} · {formatTime(flight.departure_time)}
              </p>
            </div>

            <div className="flex flex-row items-center gap-3 sm:flex-col sm:gap-2">
              <div className="h-px flex-1 bg-slate-300 sm:h-16 sm:w-px sm:flex-none" aria-hidden="true" />
              <div className="flex flex-col items-center gap-1">
                <p className="text-xs font-medium text-slate-500">
                  {formatDuration(flight.duration_minutes)}
                </p>
                <p className="text-xs text-slate-500">{formatStops(flight.stops)}</p>
              </div>
              <div className="h-px flex-1 bg-slate-300 sm:h-16 sm:w-px sm:flex-none" aria-hidden="true" />
            </div>

            <div className="sm:text-right">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Arrival
              </p>
              <p className="mt-1 font-heading text-2xl font-semibold tracking-tight text-foreground">
                {flight.destination_city}
              </p>
              <p className="text-sm text-slate-600">{flight.destination}</p>
              <p className="mt-2 text-sm text-slate-700">
                {formatFullDate(flight.arrival_time)} · {formatTime(flight.arrival_time)}
              </p>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <SeatAvailability flightId={flight.id} />
          <PriceBreakdown
            flightId={flight.id}
            initialPassengers={searchParams.passenger_count}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      {backButton}
      {content}
    </div>
  );
}