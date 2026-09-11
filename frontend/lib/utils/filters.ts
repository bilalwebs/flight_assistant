import type { TimeOfDay } from "@/lib/types";

/**
 * User-selected flight filters, applied against the current route/date via
 * POST /api/flights/filter. Every field maps 1:1 to a backend filter option.
 */
export interface FlightFilters {
  /** Airline names (e.g. "Emirates") selected from the current result set. */
  airlines: string[];
  /** null = any stops; otherwise maximum stops (backend: stops <= max_stops). */
  maxStops: number | null;
  /** null = no minimum (backend filters on base_price). */
  minPrice: number | null;
  /** null = no maximum (backend filters on base_price). */
  maxPrice: number | null;
  /** null = any time of day. */
  timeOfDay: TimeOfDay | null;
}

export const EMPTY_FILTERS: FlightFilters = {
  airlines: [],
  maxStops: null,
  minPrice: null,
  maxPrice: null,
  timeOfDay: null,
};

export const STOPS_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: "Any" },
  { value: 0, label: "Nonstop" },
  { value: 1, label: "1 stop" },
  { value: 2, label: "2 stops" },
];

export const TIME_OF_DAY_OPTIONS: { value: TimeOfDay | null; label: string }[] = [
  { value: null, label: "Any" },
  { value: "morning", label: "Morning" },
  { value: "afternoon", label: "Afternoon" },
  { value: "evening", label: "Evening" },
  { value: "night", label: "Night" },
];

/** Number of active (non-default) filter selections — used for the badge. */
export function activeFilterCount(filters: FlightFilters): number {
  return (
    (filters.airlines.length > 0 ? 1 : 0) +
    (filters.maxStops !== null ? 1 : 0) +
    (filters.minPrice !== null ? 1 : 0) +
    (filters.maxPrice !== null ? 1 : 0) +
    (filters.timeOfDay !== null ? 1 : 0)
  );
}

/** Airline names present in a result set, in first-seen order. */
export function airlineOptions(flights: Array<{ airline: string }>): string[] {
  const seen = new Set<string>();
  const options: string[] = [];
  for (const flight of flights) {
    if (!seen.has(flight.airline)) {
      seen.add(flight.airline);
      options.push(flight.airline);
    }
  }
  return options;
}