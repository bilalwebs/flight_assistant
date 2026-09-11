"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { calculateFlightPrice } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import type { PriceBreakdown as PriceBreakdownData } from "@/lib/types";
import { MAX_PASSENGERS } from "@/lib/utils/booking";

import { Skeleton } from "@/components/feedback/LoadingSkeleton";
import { Select } from "@/components/ui/Select";

const PASSENGER_OPTIONS = Array.from({ length: MAX_PASSENGERS }, (_, index) => ({
  value: String(index + 1),
  label: index === 0 ? "1 passenger" : `${index + 1} passengers`,
}));

type PriceStatus = { kind: "loading" } | { kind: "error" } | { kind: "done" };

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

interface PriceBreakdownProps {
  flightId: string;
  /** Default passenger count (e.g. count used for the search). Clamped 1–9. */
  initialPassengers?: number;
}

export function PriceBreakdown({
  flightId,
  initialPassengers = 1,
}: PriceBreakdownProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const clampedInitial = Math.min(
    MAX_PASSENGERS,
    Math.max(1, Math.trunc(initialPassengers) || 1),
  );
  const [passengerCount, setPassengerCount] = useState(clampedInitial);
  const [price, setPrice] = useState<PriceBreakdownData | null>(null);
  const [status, setStatus] = useState<PriceStatus>({ kind: "loading" });

  const load = useCallback(
    async (count: number) => {
      setStatus({ kind: "loading" });
      try {
        const result = await calculateFlightPrice(flightId, count, accessToken ?? "");
        setPrice(result);
        setStatus({ kind: "done" });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized();
          return;
        }
        setStatus({ kind: "error" });
      }
    },
    [flightId, accessToken, handleUnauthorized],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await calculateFlightPrice(
          flightId,
          clampedInitial,
          accessToken ?? "",
        );
        if (!cancelled) {
          setPrice(result);
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
    // clampedInitial derives from the prop at mount; re-fetch only on flight change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flightId, accessToken, handleUnauthorized]);

  function handleCountChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const next = Number(event.target.value);
    setPassengerCount(next);
    void load(next);
  }

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      aria-label="Price breakdown"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-heading text-base font-semibold tracking-tight text-foreground">
          Price breakdown
        </h2>
        <div className="w-40">
          <Select
            label="Passengers"
            options={PASSENGER_OPTIONS}
            value={String(passengerCount)}
            onChange={handleCountChange}
            disabled={status.kind === "loading"}
          />
        </div>
      </div>

      {status.kind === "loading" ? (
        <div className="mt-4 space-y-3" role="status" aria-label="Calculating price">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-6 w-1/3" />
        </div>
      ) : status.kind === "error" ? (
        <div className="mt-3 flex flex-col items-start gap-2">
          <p className="text-sm text-red-600" role="alert">
            Unable to calculate price.
          </p>
          <button
            type="button"
            onClick={() => void load(passengerCount)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Try again
          </button>
        </div>
      ) : price ? (
        <dl className="mt-4 divide-y divide-slate-100" aria-live="polite">
          <div className="flex items-center justify-between py-2">
            <dt className="text-sm text-slate-600">Base fare per person</dt>
            <dd className="text-sm font-medium text-slate-900">
              {formatCurrency(price.base_price_per_person, price.currency)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-2">
            <dt className="text-sm text-slate-600">Tax per person</dt>
            <dd className="text-sm font-medium text-slate-900">
              {formatCurrency(price.tax_per_person, price.currency)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-2">
            <dt className="text-sm text-slate-600">Total per person</dt>
            <dd className="text-sm font-medium text-slate-900">
              {formatCurrency(price.total_per_person, price.currency)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-2">
            <dt className="text-sm text-slate-600">Passengers</dt>
            <dd className="text-sm font-medium text-slate-900">
              {price.passenger_count}
            </dd>
          </div>
          <div className="flex items-center justify-between pt-3">
            <dt className="text-sm font-semibold text-slate-900">Grand total</dt>
            <dd className="font-heading text-xl font-semibold tracking-tight text-slate-900">
              {formatCurrency(price.grand_total, price.currency)}
            </dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}