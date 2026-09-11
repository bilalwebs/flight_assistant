"use client";

import { useMemo, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import type { Flight } from "@/lib/types";
import { airportCity } from "@/lib/utils/airports";
import {
  formatCabin,
  formatDateLabel,
  formatPassengers,
} from "@/lib/utils/date";
import {
  activeFilterCount,
  type FlightFilters as AppliedFlightFilters,
} from "@/lib/utils/filters";
import { sortFlights, type SortKey } from "@/lib/utils/sorting";
import type { SearchParams } from "@/lib/search/search-context";

import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton";
import { FlightCard } from "@/components/flights/FlightCard";
import { FlightFilters } from "@/components/flights/FlightFilters";
import { FlightSort } from "@/components/flights/FlightSort";
import { Button } from "@/components/ui/Button";

export type SearchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; flights: Flight[] }
  | { status: "error"; error: ApiError | null };

interface SearchResultsProps {
  state: SearchState;
  params: SearchParams | null;
  /** Applied filters (EMPTY_FILTERS when none active). */
  filters: AppliedFlightFilters;
  /** Bumped on every apply/clear so the filter panels resync their drafts. */
  filterKey: number;
  /** True while a filter request is in flight (previous results stay visible). */
  filtering: boolean;
  sortKey: SortKey;
  onSortChange: (key: SortKey) => void;
  onApplyFilters: (filters: AppliedFlightFilters) => void;
  onClearFilters: () => void;
  onRetry: () => void;
}

function errorCopy(error: ApiError | null): { title: string; message: string } {
  if (!error) {
    return {
      title: "We couldn't load flights right now.",
      message: "Please try again.",
    };
  }
  switch (error.code) {
    case "network":
      return {
        title: "We couldn't reach the flight service.",
        message: "Unable to reach the flight service. Please try again.",
      };
    case "validation":
      return {
        title: "Check your search",
        message: error.message || "Some of the search details are invalid.",
      };
    case "server":
      return {
        title: "We couldn't load flights right now.",
        message: "Please try again in a moment.",
      };
    case "unauthorized":
      return {
        title: "Session expired",
        message: "Please sign in again to search flights.",
      };
    default:
      return {
        title: "We couldn't load flights right now.",
        message: "Please try again.",
      };
  }
}

function routeLabel(params: SearchParams | null): string {
  if (!params) return "";
  return `${airportCity(params.origin)} → ${airportCity(params.destination)}`;
}

function hasActiveFilters(filters: AppliedFlightFilters): boolean {
  return activeFilterCount(filters) > 0;
}

export function SearchResults({
  state,
  params,
  filters,
  filterKey,
  filtering,
  sortKey,
  onSortChange,
  onApplyFilters,
  onClearFilters,
  onRetry,
}: SearchResultsProps) {
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const sortedFlights = useMemo(
    () => sortFlights(state.status === "success" ? state.flights : [], sortKey),
    [state, sortKey],
  );

  if (state.status === "idle") {
    return (
      <section className="mt-8" aria-label="Flight search results">
        <EmptyState
          title="Where are you flying?"
          description="Enter your route and travel date to discover available flights."
        />
      </section>
    );
  }

  if (state.status === "loading") {
    return (
      <section className="mt-8" aria-label="Searching for flights">
        <div className="mb-4 flex items-center gap-2">
          <span className="h-4 w-28 animate-pulse rounded bg-slate-200" aria-hidden="true" />
          <span className="h-4 w-40 animate-pulse rounded bg-slate-200" aria-hidden="true" />
        </div>
        <LoadingSkeleton count={6} />
      </section>
    );
  }

  if (state.status === "error") {
    const copy = errorCopy(state.error);
    return (
      <section className="mt-8" aria-label="Flight search results">
        <div className="mx-auto max-w-xl">
          <ErrorState title={copy.title} message={copy.message} onRetry={onRetry} />
        </div>
      </section>
    );
  }

  const activeFilters = activeFilterCount(filters);

  if (state.flights.length === 0) {
    if (hasActiveFilters(filters)) {
      return (
        <section className="mt-8" aria-label="Flight search results">
          <EmptyState
            title="No flights match your filters."
            description="Try adjusting or clearing your filters to see more options."
            action={
              <Button variant="outline" size="sm" onClick={onClearFilters}>
                Clear filters
              </Button>
            }
          />
        </section>
      );
    }
    return (
      <section className="mt-8" aria-label="Flight search results">
        <EmptyState
          title="No flights found"
          description="We couldn't find flights for this route and date. Try another date or destination."
        />
      </section>
    );
  }

  const summary = params
    ? `${routeLabel(params)} · ${formatDateLabel(params.date)} · ${formatPassengers(
        params.passenger_count,
      )} · ${formatCabin(params.cabin_class)}`
    : "";

  const desktopFilters = (
    <FlightFilters
      key={`desktop-${filterKey}`}
      flights={state.flights}
      applied={filters}
      loading={filtering}
      onApply={onApplyFilters}
      onClear={onClearFilters}
    />
  );

  const mobileFilters = (
    <FlightFilters
      key={`mobile-${filterKey}`}
      flights={state.flights}
      applied={filters}
      loading={filtering}
      onApply={onApplyFilters}
      onClear={onClearFilters}
    />
  );

  return (
    <section className="mt-8" aria-label="Flight search results" aria-busy={filtering || undefined}>
      <div
        className="mb-5 flex flex-col gap-1"
        aria-live="polite"
        aria-atomic="true"
      >
        <h2 className="font-heading text-lg font-semibold tracking-tight text-foreground">
          {sortedFlights.length} {sortedFlights.length === 1 ? "flight" : "flights"} found
        </h2>
        <p className="text-sm text-slate-600">{summary}</p>
      </div>

      <div className="lg:grid lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start lg:gap-6">
        <aside className="hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-card lg:block">
          <h3 className="mb-4 font-heading text-sm font-semibold uppercase tracking-wide text-slate-500">
            Filters
          </h3>
          {desktopFilters}
        </aside>

        <div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <Button
              variant="outline"
              size="sm"
              className="lg:hidden"
              onClick={() => setMobileFiltersOpen((current) => !current)}
              aria-expanded={mobileFiltersOpen}
              aria-controls="mobile-filters"
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
                <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
              </svg>
              Filters
              {activeFilters > 0 ? (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-white">
                  {activeFilters}
                </span>
              ) : null}
            </Button>

            <FlightSort
              value={sortKey}
              onChange={onSortChange}
              disabled={filtering}
            />
          </div>

          {mobileFiltersOpen ? (
            <div
              id="mobile-filters"
              className="mb-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card lg:hidden"
            >
              <h3 className="mb-4 font-heading text-sm font-semibold uppercase tracking-wide text-slate-500">
                Filters
              </h3>
              {mobileFilters}
            </div>
          ) : null}

          {filtering ? (
            <p className="mb-3 text-sm text-slate-500" aria-live="polite">
              Applying filters…
            </p>
          ) : null}

          <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
            {sortedFlights.map((flight) => (
              <FlightCard key={flight.id} flight={flight} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}