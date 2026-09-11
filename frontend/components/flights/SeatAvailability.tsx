"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { getSeatAvailability } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import type { SeatAvailability as SeatAvailabilityData } from "@/lib/types";

import { Skeleton } from "@/components/feedback/LoadingSkeleton";

type AvailabilityStatus = { kind: "loading" } | { kind: "error" } | { kind: "done" };

interface SeatAvailabilityProps {
  flightId: string;
}

export function SeatAvailability({ flightId }: SeatAvailabilityProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const [data, setData] = useState<SeatAvailabilityData | null>(null);
  const [status, setStatus] = useState<AvailabilityStatus>({ kind: "loading" });

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const result = await getSeatAvailability(flightId, accessToken ?? "");
      setData(result);
      setStatus({ kind: "done" });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return;
      }
      setStatus({ kind: "error" });
    }
  }, [flightId, accessToken, handleUnauthorized]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await getSeatAvailability(flightId, accessToken ?? "");
        if (!cancelled) {
          setData(result);
          setStatus({ kind: "done" });
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 401) {
            handleUnauthorized();
            return;
          }
          setStatus({ kind: "error" });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [flightId, accessToken, handleUnauthorized]);

  const price = status.kind === "done" && data ? (data.available_seats / data.total_seats) * 100 : 0;
  const lowStock = data !== null && data.available_seats > 0 && data.available_seats <= 5;

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      aria-label="Seat availability"
    >
      <h2 className="font-heading text-base font-semibold tracking-tight text-foreground">
        Seat availability
      </h2>

      {status.kind === "loading" ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-4 w-40" />
        </div>
      ) : status.kind === "error" ? (
        <div className="mt-3 flex flex-col items-start gap-2">
          <p className="text-sm text-red-600" role="alert">
            Seat availability unavailable.
          </p>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Try again
          </button>
        </div>
      ) : data ? (
        <div className="mt-4" aria-live="polite">
          <div className="flex items-end justify-between gap-3">
            <p className="font-heading text-2xl font-semibold tracking-tight text-slate-900">
              {data.available_seats}
              <span className="ml-1 text-sm font-normal text-slate-500">
                of {data.total_seats} seats
              </span>
            </p>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                data.available_seats === 0
                  ? "bg-red-100 text-red-700"
                  : lowStock
                    ? "bg-amber-100 text-amber-800"
                    : "bg-emerald-100 text-emerald-800"
              }`}
            >
              {data.available_seats === 0
                ? "Sold out"
                : lowStock
                  ? `Only ${data.available_seats} ${data.available_seats === 1 ? "seat" : "seats"} left`
                  : `${data.available_seats} seats available`}
            </span>
          </div>
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"
            role="presentation"
          >
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                data.available_seats === 0
                  ? "bg-red-500"
                  : lowStock
                    ? "bg-amber-400"
                    : "bg-emerald-500"
              }`}
              style={{ width: `${Math.max(price, 2)}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Real-time availability for flight {data.flight_number}.
          </p>
        </div>
      ) : null}
    </section>
  );
}