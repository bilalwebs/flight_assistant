import type { Flight } from "@/lib/types";
import {
  formatCabin,
  formatDuration,
  formatPrice,
  formatStops,
  formatTime,
} from "@/lib/utils/date";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function seatsLabel(available: number): string {
  if (available <= 0) return "Sold out";
  return `${available} seat${available === 1 ? "" : "s"} left`;
}

export function FlightCard({ flight }: { flight: Flight }) {
  return (
    <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-xs font-semibold text-primary-700">
            {flight.airline_code}
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">{flight.airline}</p>
            <p className="text-xs text-slate-500">
              {flight.airline_code} · Flight {flight.flight_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant="info">{formatCabin(flight.cabin_class)}</Badge>
          <Badge variant={flight.stops === 0 ? "success" : "default"}>
            {formatStops(flight.stops)}
          </Badge>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 md:items-center">
        <div>
          <p className="font-heading text-xl font-semibold tracking-tight text-foreground">
            {formatTime(flight.departure_time)}
          </p>
          <p className="mt-0.5 text-sm text-slate-700">{flight.origin_city}</p>
          <p className="text-xs text-slate-500">{flight.origin}</p>
        </div>

        <div className="flex flex-row items-center gap-2 md:flex-col md:gap-1">
          <div className="h-px flex-1 bg-slate-300 md:h-4 md:w-full md:flex-none md:bg-transparent" aria-hidden="true" />
          <p className="whitespace-nowrap text-xs font-medium text-slate-500">
            {formatDuration(flight.duration_minutes)}
          </p>
          <div className="h-px flex-1 bg-slate-300 md:h-4 md:w-full md:flex-none md:bg-transparent" aria-hidden="true" />
        </div>

        <div className="md:text-right">
          <p className="font-heading text-xl font-semibold tracking-tight text-foreground">
            {formatTime(flight.arrival_time)}
          </p>
          <p className="mt-0.5 text-sm text-slate-700">{flight.destination_city}</p>
          <p className="text-xs text-slate-500">{flight.destination}</p>
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between gap-3 border-t border-slate-100 pt-4">
        <div>
          <p className="text-xs text-slate-500">per traveler</p>
          <p className="font-heading text-2xl font-semibold tracking-tight text-slate-900">
            {formatPrice(flight.base_price)}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span
            className={`text-xs ${
              flight.available_seats === 0
                ? "font-medium text-red-600"
                : "text-slate-600"
            }`}
            title={`${flight.available_seats} of ${flight.total_seats} seats`}
          >
            {seatsLabel(flight.available_seats)}
          </span>
          <Button variant="outline" size="sm" href={`/flights/${flight.id}`}>
            View Details
          </Button>
        </div>
      </div>
    </article>
  );
}