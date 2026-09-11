"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { calculateFlightPrice } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import type { Flight, PriceBreakdown as PriceBreakdownData } from "@/lib/types";
import {
  formatCabin,
  formatFullDate,
  formatPrice,
  formatTime,
} from "@/lib/utils/date";
import type {
  ContactFormValues,
  PassengerFormValues,
} from "@/lib/utils/booking";
import {
  PASSENGER_TYPE_LABELS,
  clampPassengerCount,
} from "@/lib/utils/booking";

import { Skeleton } from "@/components/feedback/LoadingSkeleton";

type PriceStatus =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "done" };

interface BookingReviewProps {
  flight: Flight;
  passengers: PassengerFormValues[];
  contact: ContactFormValues;
}

/** Server-side estimate used pre-booking; the created booking becomes authoritative. */
export function BookingReview({
  flight,
  passengers,
  contact,
}: BookingReviewProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const count = clampPassengerCount(passengers.length);
  const [price, setPrice] = useState<PriceBreakdownData | null>(null);
  const [priceStatus, setPriceStatus] = useState<PriceStatus>({
    kind: "loading",
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await calculateFlightPrice(
          flight.id,
          count,
          accessToken ?? "",
        );
        if (!cancelled) {
          setPrice(result);
          setPriceStatus({ kind: "done" });
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 401) {
            handleUnauthorized();
            return;
          }
          setPriceStatus({ kind: "error" });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [flight.id, count, accessToken, handleUnauthorized]);

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      aria-labelledby="booking-review-heading"
    >
      <h2
        id="booking-review-heading"
        className="font-heading text-base font-semibold tracking-tight text-foreground"
      >
        Booking review
      </h2>

      <div className="mt-4 space-y-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Flight
          </p>
          <p className="mt-1 text-sm font-medium text-foreground">
            {flight.airline} · Flight {flight.flight_number}
          </p>
          <p className="text-sm text-slate-600">
            {flight.origin_city} ({flight.origin}) → {flight.destination_city} (
            {flight.destination})
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {formatFullDate(flight.departure_time)} · {formatTime(flight.departure_time)} →{" "}
            {formatTime(flight.arrival_time)}
          </p>
          <p className="mt-1 text-sm text-slate-600">{formatCabin(flight.cabin_class)} class</p>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Passengers
          </p>
          <ul className="mt-1 space-y-0.5">
            {passengers.map((passenger, index) => (
              <li key={index} className="text-sm text-slate-700">
                {PASSENGER_TYPE_LABELS[passenger.passenger_type]} ·{" "}
                {[passenger.first_name.trim(), passenger.last_name.trim()]
                  .filter(Boolean)
                  .join(" ") || "—"}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Contact
          </p>
          <p className="mt-1 text-sm text-slate-700">{contact.email.trim() || "—"}</p>
          <p className="text-sm text-slate-700">{contact.phone.trim() || "—"}</p>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Estimated total
          </p>
          {priceStatus.kind === "loading" ? (
            <div className="mt-2 space-y-2" role="status" aria-label="Calculating price">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-6 w-32" />
            </div>
          ) : priceStatus.kind === "error" ? (
            <p className="mt-2 text-sm text-red-600" role="alert">
              Unable to estimate the price right now.
            </p>
          ) : price ? (
            <dl className="mt-2 divide-y divide-slate-100">
              <div className="flex items-center justify-between py-1.5">
                <dt className="text-sm text-slate-600">Base fare per person</dt>
                <dd className="text-sm font-medium text-slate-900">
                  {formatPrice(price.base_price_per_person)}
                </dd>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <dt className="text-sm text-slate-600">Tax per person</dt>
                <dd className="text-sm font-medium text-slate-900">
                  {formatPrice(price.tax_per_person)}
                </dd>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <dt className="text-sm text-slate-600">Total for {price.passenger_count}</dt>
                <dd className="font-heading text-lg font-semibold tracking-tight text-foreground">
                  {formatPrice(price.grand_total)}
                </dd>
              </div>
            </dl>
          ) : null}
          {price ? (
            <p className="mt-2 text-xs text-slate-500">
              Estimate from the server. The final total is set when the booking
              is created.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}