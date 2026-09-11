"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Flight, TimeOfDay } from "@/lib/types";
import {
  airlineOptions,
  STOPS_OPTIONS,
  TIME_OF_DAY_OPTIONS,
  type FlightFilters,
} from "@/lib/utils/filters";

const TIME_OF_DAY_SELECT_OPTIONS = TIME_OF_DAY_OPTIONS.map((option) => ({
  value: option.value ?? "",
  label: option.label,
}));

interface FilterDraft {
  airlines: string[];
  maxStops: number | null;
  minPrice: string;
  maxPrice: string;
  timeOfDay: TimeOfDay | null;
}

function toDraft(filters: FlightFilters): FilterDraft {
  return {
    airlines: filters.airlines,
    maxStops: filters.maxStops,
    minPrice: filters.minPrice !== null ? String(filters.minPrice) : "",
    maxPrice: filters.maxPrice !== null ? String(filters.maxPrice) : "",
    timeOfDay: filters.timeOfDay,
  };
}

function priceValidation(draft: FilterDraft): string | null {
  const minRaw = draft.minPrice.trim();
  const maxRaw = draft.maxPrice.trim();

  const min = minRaw === "" ? null : Number(minRaw);
  const max = maxRaw === "" ? null : Number(maxRaw);

  if (min !== null && (!Number.isFinite(min) || min < 0)) {
    return "Enter a valid minimum price.";
  }
  if (max !== null && (!Number.isFinite(max) || max < 0)) {
    return "Enter a valid maximum price.";
  }
  if (min !== null && max !== null && min > max) {
    return "Minimum price can't exceed the maximum.";
  }
  return null;
}

interface FlightFiltersProps {
  flights: Flight[];
  /** Currently applied filters (EMPTY_FILTERS when none active). */
  applied: FlightFilters;
  /** True while a filter request is in flight. */
  loading: boolean;
  onApply: (filters: FlightFilters) => void;
  onClear: () => void;
}

export function FlightFilters({
  flights,
  applied,
  loading,
  onApply,
  onClear,
}: FlightFiltersProps) {
  const [draft, setDraft] = useState<FilterDraft>(() => toDraft(applied));
  const priceError = priceValidation(draft);
  const hasChanges =
    draft.airlines.length !== applied.airlines.length ||
    draft.maxStops !== applied.maxStops ||
    (draft.minPrice.trim() === "") !== (applied.minPrice === null) ||
    (draft.maxPrice.trim() === "") !== (applied.maxPrice === null) ||
    draft.timeOfDay !== applied.timeOfDay;

  const airlines = airlineOptions(flights);
  const hasAppliedFilters =
    applied.airlines.length > 0 ||
    applied.maxStops !== null ||
    applied.minPrice !== null ||
    applied.maxPrice !== null ||
    applied.timeOfDay !== null;
  const canClear = hasChanges || hasAppliedFilters;

  function toggleAirline(airline: string) {
    setDraft((current) => ({
      ...current,
      airlines: current.airlines.includes(airline)
        ? current.airlines.filter((value) => value !== airline)
        : [...current.airlines, airline],
    }));
  }

  function handleApply() {
    if (loading || priceError) return;
    onApply({
      airlines: draft.airlines,
      maxStops: draft.maxStops,
      minPrice: draft.minPrice.trim() === "" ? null : Number(draft.minPrice),
      maxPrice: draft.maxPrice.trim() === "" ? null : Number(draft.maxPrice),
      timeOfDay: draft.timeOfDay,
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="space-y-6">
        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">
            Airlines
          </legend>
          {airlines.length === 0 ? (
            <p className="mt-1.5 text-xs text-slate-500">No airlines to filter.</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1.5">
              {airlines.map((airline) => {
                const checked = draft.airlines.includes(airline);
                return (
                  <li key={airline}>
                    <label
                      className={`flex cursor-pointer items-center gap-2.5 rounded-lg border px-2.5 py-2 text-sm transition-colors ${
                        checked
                          ? "border-primary-300 bg-primary-50 text-primary-800"
                          : "border-transparent text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleAirline(airline)}
                        disabled={loading}
                        className="h-4 w-4 rounded border-slate-300 accent-primary disabled:cursor-not-allowed disabled:opacity-50"
                      />
                      <span>{airline}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">
            Stops
          </legend>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {STOPS_OPTIONS.map((option) => {
              const checked = draft.maxStops === option.value;
              return (
                <label
                  key={option.label}
                  className={`cursor-pointer rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    checked
                      ? "border-primary-400 bg-primary-600 text-white"
                      : "border-slate-300 bg-white text-slate-700 hover:border-primary-400 hover:text-primary-700"
                  }`}
                >
                  <input
                    type="radio"
                    name="max-stops"
                    value={option.value ?? ""}
                    checked={checked}
                    onChange={() => setDraft((current) => ({ ...current, maxStops: option.value }))}
                    disabled={loading}
                    className="sr-only"
                  />
                  {option.label}
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">
            Price per traveler
          </legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Input
              label="Minimum"
              type="number"
              min={0}
              step="1"
              inputMode="numeric"
              placeholder="0"
              value={draft.minPrice}
              onChange={(event) =>
                setDraft((current) => ({ ...current, minPrice: event.target.value }))
              }
              disabled={loading}
              aria-label="Minimum price"
            />
            <Input
              label="Maximum"
              type="number"
              min={0}
              step="1"
              inputMode="numeric"
              placeholder="Any"
              value={draft.maxPrice}
              onChange={(event) =>
                setDraft((current) => ({ ...current, maxPrice: event.target.value }))
              }
              disabled={loading}
              aria-label="Maximum price"
            />
          </div>
          {priceError ? (
            <p className="mt-1.5 text-xs text-red-600" role="alert">
              {priceError}
            </p>
          ) : null}
        </fieldset>

        <div>
          <Select
            label="Time of day"
            options={TIME_OF_DAY_SELECT_OPTIONS}
            value={draft.timeOfDay ?? ""}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                timeOfDay:
                  event.target.value === ""
                    ? null
                    : (event.target.value as TimeOfDay),
              }))
            }
            disabled={loading}
          />
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t border-slate-100 pt-4">
        <Button
          size="sm"
          onClick={handleApply}
          loading={loading}
          disabled={loading || priceError !== null}
          fullWidth
        >
          Apply Filters
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          disabled={loading || !canClear}
        >
          Clear filters
        </Button>
      </div>
    </div>
  );
}