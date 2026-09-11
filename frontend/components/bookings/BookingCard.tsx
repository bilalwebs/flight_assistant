import Link from "next/link";

import type { BookingResponse, Flight } from "@/lib/types";
import { formatFullDate, formatPassengers, formatPrice, formatTime } from "@/lib/utils/date";

import { BookingStatusBadge } from "@/components/bookings/BookingStatusBadge";

interface BookingCardProps {
  booking: BookingResponse;
  flight?: Flight | null;
}

export function BookingCard({ booking, flight }: BookingCardProps) {
  const departureTime = flight ? flight.departure_time : null;

  return (
    <Link
      href={`/bookings/${booking.pnr}`}
      aria-label={`View booking ${booking.pnr} ${booking.status}`}
      className="group flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-colors hover:border-primary-300 hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-base font-semibold tracking-wider text-foreground">
          {booking.pnr}
        </span>
        <BookingStatusBadge status={booking.status} />
      </div>

      {flight ? (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-foreground">
            {flight.airline_code} {flight.flight_number}
          </p>
          <p className="text-sm text-slate-600" aria-label="Route">
            {flight.origin} → {flight.destination}
            <span className="text-slate-400"> · {flight.origin_city} → {flight.destination_city}</span>
          </p>
        </div>
      ) : (
        <p className="text-sm text-slate-500">Flight details unavailable</p>
      )}

      <dl className="mt-auto grid grid-cols-2 gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-sm">
        <div className="flex flex-col">
          <dt className="text-xs text-slate-500">Departure</dt>
          <dd className="font-medium text-foreground">
            {departureTime ? (
              <>
                {formatFullDate(departureTime)}
                <span className="ml-1 text-slate-500">· {formatTime(departureTime)}</span>
              </>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <div className="flex flex-col items-end text-right">
          <dt className="text-xs text-slate-500">Passengers</dt>
          <dd className="font-medium text-foreground">{formatPassengers(booking.passenger_count)}</dd>
        </div>
        <div className="flex flex-col">
          <dt className="text-xs text-slate-500">Cabin</dt>
          <dd className="font-medium capitalize text-foreground">{booking.cabin_class}</dd>
        </div>
        <div className="flex flex-col items-end text-right">
          <dt className="text-xs text-slate-500">Total</dt>
          <dd className="font-heading text-base font-semibold text-foreground">
            {formatPrice(booking.total_amount)}
          </dd>
        </div>
      </dl>
    </Link>
  );
}