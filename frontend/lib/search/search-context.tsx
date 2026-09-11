"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { tomorrowISO } from "@/lib/utils/date";
import type { CabinClass, Flight } from "@/lib/types";

export interface SearchParams {
  origin: string;
  destination: string;
  /** YYYY-MM-DD, user local date. */
  date: string;
  passenger_count: number;
  cabin_class: CabinClass;
}

interface SearchContextValue {
  searchParams: SearchParams;
  /** Partial merge — values keep searching on navigation within the app. */
  setSearchParams: (params: Partial<SearchParams>) => void;
  clearSearch: () => void;
  /** True once the user has submitted at least one search this session. */
  hasSearched: boolean;
  /**
   * Latest successful search results (kept in memory only). Lets the
   * details page "Back to search results" restore the previous result set.
   */
  lastResults: Flight[] | null;
  setLastResults: (results: Flight[] | null) => void;
}

const SearchContext = createContext<SearchContextValue | undefined>(undefined);

function defaultSearchParams(): SearchParams {
  return {
    origin: "",
    destination: "",
    date: tomorrowISO(),
    passenger_count: 1,
    cabin_class: "economy",
  };
}

export function SearchProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParamsState] = useState<SearchParams>(defaultSearchParams);
  const [hasSearched, setHasSearched] = useState(false);
  const [lastResults, setLastResults] = useState<Flight[] | null>(null);

  const setSearchParams = useCallback((params: Partial<SearchParams>) => {
    setSearchParamsState((current) => ({ ...current, ...params }));
    setHasSearched(true);
  }, []);

  const clearSearch = useCallback(() => {
    setSearchParamsState(defaultSearchParams());
    setHasSearched(false);
    setLastResults(null);
  }, []);

  const value = useMemo<SearchContextValue>(
    () => ({
      searchParams,
      setSearchParams,
      clearSearch,
      hasSearched,
      lastResults,
      setLastResults,
    }),
    [searchParams, setSearchParams, clearSearch, hasSearched, lastResults],
  );

  return <SearchContext.Provider value={value}>{children}</SearchContext.Provider>;
}

export function useSearch(): SearchContextValue {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error("useSearch must be used within a SearchProvider");
  }
  return context;
}