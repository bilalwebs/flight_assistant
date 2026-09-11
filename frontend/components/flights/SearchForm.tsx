"use client";

import { useState, type FormEvent } from "react";

import { useSearch, type SearchParams } from "@/lib/search/search-context";
import { AIRPORTS, airportHint } from "@/lib/utils/airports";
import { todayISO } from "@/lib/utils/date";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

const AIRPORT_OPTIONS = Object.entries(AIRPORTS).map(([value, city]) => ({
  value,
  label: `${value} — ${city}`,
}));

const PASSENGER_OPTIONS = Array.from({ length: 9 }, (_, index) => ({
  value: String(index + 1),
  label: index === 0 ? "1 passenger" : `${index + 1} passengers`,
}));

const CABIN_OPTIONS = [
  { value: "economy", label: "Economy" },
  { value: "business", label: "Business" },
];

/** Uppercase IATA code (max 3 letters). */
function normalizeIATA(value: string): string {
  return value
    .toUpperCase()
    .replace(/[^A-Z]/g, "")
    .slice(0, 3);
}

interface FormErrors {
  origin?: string;
  destination?: string;
  date?: string;
  passengers?: string;
  cabin?: string;
}

interface SearchFormProps {
  onSearch: (params: SearchParams) => void;
  loading: boolean;
}

export function SearchForm({ onSearch, loading }: SearchFormProps) {
  const { searchParams } = useSearch();

  const [origin, setOrigin] = useState(searchParams.origin);
  const [destination, setDestination] = useState(searchParams.destination);
  const [date, setDate] = useState(searchParams.date);
  const [passengers, setPassengers] = useState(String(searchParams.passenger_count));
  const [cabin, setCabin] = useState<SearchParams["cabin_class"]>(searchParams.cabin_class);
  const [errors, setErrors] = useState<FormErrors>({});

  function clearFieldError(field: keyof FormErrors) {
    setErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function handleSwap() {
    setOrigin(destination);
    setDestination(origin);
    setErrors((current) => {
      const next = { ...current };
      delete next.origin;
      delete next.destination;
      return next;
    });
  }

  function validate(): FormErrors {
    const next: FormErrors = {};

    if (!origin) {
      next.origin = "Origin is required.";
    } else if (!/^[A-Z]{3}$/.test(origin)) {
      next.origin = "Enter a 3-letter airport code (e.g., KHI).";
    }

    if (!destination) {
      next.destination = "Destination is required.";
    } else if (!/^[A-Z]{3}$/.test(destination)) {
      next.destination = "Enter a 3-letter airport code (e.g., DXB).";
    }

    if (origin && destination && origin === destination) {
      next.destination = "Origin and destination must be different.";
    }

    if (!date) {
      next.date = "Departure date is required.";
    } else if (date < todayISO()) {
      next.date = "Departure date can't be in the past.";
    }

    const count = Number(passengers);
    if (!Number.isInteger(count) || count < 1) {
      next.passengers = "Select at least 1 passenger.";
    }

    if (cabin !== "economy" && cabin !== "business") {
      next.cabin = "Choose a cabin class.";
    }

    return next;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    const next = validate();
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    onSearch({
      origin,
      destination,
      date,
      passenger_count: Number(passengers),
      cabin_class: cabin,
    });
  }

  return (
    <form
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card sm:p-6"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-3">
        <div className="w-full md:flex-1">
          <Input
            label="Origin"
            placeholder="KHI"
            autoComplete="off"
            list="airport-hints"
            value={origin}
            onChange={(event) => {
              setOrigin(normalizeIATA(event.target.value));
              clearFieldError("origin");
            }}
            error={errors.origin}
            helperText={airportHint(origin)}
            maxLength={3}
            required
            aria-label="Origin airport code"
          />
        </div>

        <div className="flex justify-center md:shrink-0">
          <button
            type="button"
            onClick={handleSwap}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 shadow-sm transition-colors hover:border-primary-400 hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            aria-label="Swap origin and destination"
            title="Swap origin and destination"
            disabled={loading}
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
              <path d="m7 8 5 5 5-5" />
              <path d="M7 16h10" />
            </svg>
          </button>
        </div>

        <div className="w-full md:flex-1">
          <Input
            label="Destination"
            placeholder="DXB"
            autoComplete="off"
            list="airport-hints"
            value={destination}
            onChange={(event) => {
              setDestination(normalizeIATA(event.target.value));
              clearFieldError("destination");
            }}
            error={errors.destination}
            helperText={airportHint(destination)}
            maxLength={3}
            required
            aria-label="Destination airport code"
          />
        </div>

        <div className="w-full md:w-44 md:shrink-0">
          <Input
            label="Departure"
            type="date"
            value={date}
            min={todayISO()}
            onChange={(event) => {
              setDate(event.target.value);
              clearFieldError("date");
            }}
            error={errors.date}
            required
          />
        </div>

        <div className="w-full md:w-32 md:shrink-0">
          <Select
            label="Passengers"
            options={PASSENGER_OPTIONS}
            value={passengers}
            onChange={(event) => {
              setPassengers(event.target.value);
              clearFieldError("passengers");
            }}
            error={errors.passengers}
            required
          />
        </div>

        <div className="w-full md:w-40 md:shrink-0">
          <Select
            label="Cabin"
            options={CABIN_OPTIONS}
            value={cabin}
            onChange={(event) => {
              setCabin(event.target.value as SearchParams["cabin_class"]);
              clearFieldError("cabin");
            }}
            error={errors.cabin}
            required
          />
        </div>
      </div>

      <datalist id="airport-hints">
        {AIRPORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </datalist>

      <div className="mt-5 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
        <Button type="submit" size="lg" loading={loading} disabled={loading} className="w-full sm:w-auto">
          {loading ? "Searching flights..." : "Search flights"}
        </Button>
        <p className="text-xs text-slate-500">
          Use IATA airport codes, e.g. KHI — Karachi.
        </p>
      </div>
    </form>
  );
}