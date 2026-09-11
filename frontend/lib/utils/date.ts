/**
 * Pure date/time/duration/currency helpers for the flight UI.
 * All helpers work with the caller's local timezone; none hardcode dates.
 */

/** Local date of `date` as YYYY-MM-DD (safe for <input type="date">). */
export function toISODate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Local date for `days` from now, e.g. 1 = tomorrow. */
export function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

/** Today's local date as YYYY-MM-DD. */
export function todayISO(): string {
  return toISODate(new Date());
}

/** Tomorrow's local date as YYYY-MM-DD. */
export function tomorrowISO(): string {
  return toISODate(addDays(new Date(), 1));
}

/** Date (YYYY-MM-DD) plus `days` days, as YYYY-MM-DD. */
export function addDaysISO(dateISO: string, days: number): string {
  return toISODate(addDays(new Date(dateISO + "T00:00:00"), days));
}

/** Friendly label for a YYYY-MM-DD: "Today", "Tomorrow", or "Wed, Sep 9". */
export function formatDateLabel(dateISO: string): string {
  if (dateISO === todayISO()) return "Today";
  if (dateISO === tomorrowISO()) return "Tomorrow";
  const date = new Date(dateISO + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/** Human time for an ISO timestamp in the user's local timezone, e.g. "10:30 AM". */
export function formatTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/** Full date for an ISO timestamp, e.g. "Tue, Sep 8, 2026". */
export function formatFullDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** "2h 15m" from a minute count. */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/** "Nonstop", "1 stop", "2 stops". */
export function formatStops(stops: number): string {
  if (stops === 0) return "Nonstop";
  return `${stops} ${stops === 1 ? "stop" : "stops"}`;
}

/** Title-cased cabin label, e.g. "Economy". */
export function formatCabin(cabinClass: string): string {
  switch (cabinClass) {
    case "business":
      return "Business";
    case "first":
      return "First";
    default:
      return "Economy";
  }
}

/** "$150.00" — backend fares are quoted in USD. */
export function formatPrice(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/** "1 passenger" / "3 passengers". */
export function formatPassengers(count: number): string {
  return `${count} ${count === 1 ? "passenger" : "passengers"}`;
}