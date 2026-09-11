"use client";

import { useCallback, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { filterFlights, searchFlights } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import { useSearch, type SearchParams } from "@/lib/search/search-context";
import type { Flight, FlightFilterRequest } from "@/lib/types";
import { activeFilterCount, EMPTY_FILTERS, type FlightFilters } from "@/lib/utils/filters";
import type { SortKey } from "@/lib/utils/sorting";

import { SearchForm } from "@/components/flights/SearchForm";
import {
  SearchResults,
  type SearchState,
} from "@/components/flights/SearchResults";

function mergeFlights(batches: Flight[][]): Flight[] {
  return Array.from(
    new Map(batches.flat().map((flight) => [flight.id, flight])).values(),
  );
}

export function FlightSearchBoard() {
  const { accessToken, handleUnauthorized } = useAuth();
  const { searchParams, setSearchParams, lastResults, setLastResults } = useSearch();

  const [state, setState] = useState<SearchState>(() =>
    lastResults ? { status: "success", flights: lastResults } : { status: "idle" },
  );
  const [lastParams, setLastParams] = useState<SearchParams | null>(() =>
    lastResults ? searchParams : null,
  );
  const [filters, setFilters] = useState<FlightFilters>(EMPTY_FILTERS);
  const [filterKey, setFilterKey] = useState(0);
  const [filtering, setFiltering] = useState(false);
  const [errorFromFilter, setErrorFromFilter] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("recommended");

  const runSearch = useCallback(
    async (params: SearchParams) => {
      setSearchParams(params);
      setLastParams(params);
      setFilters(EMPTY_FILTERS);
      setFilterKey((key) => key + 1);
      setSortKey("recommended");
      setErrorFromFilter(false);
      setState({ status: "loading" });

      try {
        const flights = await searchFlights(
          {
            origin: params.origin,
            destination: params.destination,
            date: params.date,
            cabin_class: params.cabin_class,
          },
          accessToken ?? "",
        );
        setState({ status: "success", flights });
        setLastResults(flights);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          // Existing auth layer clears the session; ProtectedRoute redirects.
          handleUnauthorized();
          setState({ status: "idle" });
          return;
        }
        setState({
          status: "error",
          error: error instanceof ApiError ? error : null,
        });
      }
    },
    [accessToken, handleUnauthorized, setSearchParams, setLastResults],
  );

  const applyFilters = useCallback(
    async (next: FlightFilters) => {
      if (!lastParams) return;

      setFilters(next);
      setFilterKey((key) => key + 1);
      setErrorFromFilter(false);
      setFiltering(true);

      const base: FlightFilterRequest = {
        origin: lastParams.origin,
        destination: lastParams.destination,
        date: lastParams.date,
        cabin_class: lastParams.cabin_class,
      };

      const buildRequest = (selection: FlightFilters): FlightFilterRequest => ({
        ...base,
        airline: selection.airlines.length === 1 ? selection.airlines[0] : undefined,
        max_stops: selection.maxStops ?? undefined,
        min_price: selection.minPrice ?? undefined,
        max_price: selection.maxPrice ?? undefined,
        time_of_day: selection.timeOfDay ?? undefined,
      });

      try {
        let flights: Flight[];
        if (next.airlines.length <= 1) {
          flights = await filterFlights(buildRequest(next), accessToken ?? "");
        } else {
          // The backend accepts one airline per request; merge real results
          // across the selected airlines to honor multi-select.
          const batches = await Promise.all(
            next.airlines.map((airline) =>
              filterFlights({ ...buildRequest(next), airline }, accessToken ?? ""),
            ),
          );
          flights = mergeFlights(batches);
        }
        setState({ status: "success", flights });
        setLastResults(flights);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized();
          setState({ status: "idle" });
          return;
        }
        setErrorFromFilter(true);
        setState({
          status: "error",
          error: error instanceof ApiError ? error : null,
        });
      } finally {
        setFiltering(false);
      }
    },
    [lastParams, accessToken, handleUnauthorized, setLastResults],
  );

  const clearFilters = useCallback(() => {
    if (lastParams) {
      void runSearch(lastParams);
    } else {
      setFilters(EMPTY_FILTERS);
      setFilterKey((key) => key + 1);
    }
  }, [lastParams, runSearch]);

  const handleSearch = useCallback(
    (params: SearchParams) => {
      void runSearch(params);
    },
    [runSearch],
  );

  const handleRetry = useCallback(() => {
    if (errorFromFilter && activeFilterCount(filters) > 0) {
      void applyFilters(filters);
    } else if (lastParams) {
      void runSearch(lastParams);
    }
  }, [errorFromFilter, filters, applyFilters, lastParams, runSearch]);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          Find your next flight
        </h1>
        <p className="mt-1.5 text-sm text-slate-600 sm:text-base">
          Search available flights, filter the results, and compare your options.
        </p>
      </header>

      <SearchForm
        onSearch={handleSearch}
        loading={state.status === "loading"}
      />

      <SearchResults
        state={state}
        params={lastParams}
        filters={filters}
        filterKey={filterKey}
        filtering={filtering}
        sortKey={sortKey}
        onSortChange={setSortKey}
        onApplyFilters={(next) => void applyFilters(next)}
        onClearFilters={clearFilters}
        onRetry={handleRetry}
      />
    </div>
  );
}