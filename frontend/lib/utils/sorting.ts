import type { Flight } from "@/lib/types";

/**
 * Client-side result ordering. All fields required for sorting already exist
 * in the `Flight` response, so no backend call is needed. The original
 * (backend) order is always preserved for "recommended".
 */
export type SortKey =
  | "recommended"
  | "price_asc"
  | "price_desc"
  | "departure"
  | "duration";

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "recommended", label: "Recommended" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "departure", label: "Departure: Earliest" },
  { value: "duration", label: "Duration: Shortest" },
];

/** Returns a NEW array — the input is never mutated. */
export function sortFlights(flights: Flight[], key: SortKey): Flight[] {
  const sorted = [...flights];

  switch (key) {
    case "price_asc":
      sorted.sort(
        (a, b) =>
          a.base_price - b.base_price || a.duration_minutes - b.duration_minutes,
      );
      break;
    case "price_desc":
      sorted.sort(
        (a, b) =>
          b.base_price - a.base_price || a.duration_minutes - b.duration_minutes,
      );
      break;
    case "departure":
      sorted.sort(
        (a, b) =>
          new Date(a.departure_time).getTime() -
          new Date(b.departure_time).getTime(),
      );
      break;
    case "duration":
      sorted.sort(
        (a, b) =>
          a.duration_minutes - b.duration_minutes || a.base_price - b.base_price,
      );
      break;
    default:
      break;
  }

  return sorted;
}