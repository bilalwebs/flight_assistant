/**
 * UI hints for the seeded routes — NOT a real airport database.
 * Used to label inputs and build result summaries from IATA codes.
 */
export const AIRPORTS: Record<string, string> = {
  KHI: "Karachi",
  DXB: "Dubai",
  IST: "Istanbul",
  LHE: "Lahore",
  LHR: "London",
  RUH: "Riyadh",
  ISB: "Islamabad",
  DOH: "Doha",
};

/** City name for an IATA code, falling back to the code itself. */
export function airportCity(code: string): string {
  return AIRPORTS[code] ?? code;
}

/** "KHI — Karachi" hint for an IATA code, or undefined when unknown. */
export function airportHint(code: string): string | undefined {
  const city = AIRPORTS[code];
  return city ? `${code} — ${city}` : undefined;
}