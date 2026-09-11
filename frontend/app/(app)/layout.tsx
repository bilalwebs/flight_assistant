"use client";

import type { ReactNode } from "react";

import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { SearchProvider } from "@/lib/search/search-context";

/**
 * Route group for authenticated feature pages. Search parameters are kept in
 * SearchProvider so they survive navigation within the app. Children are
 * gated behind ProtectedRoute.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <SearchProvider>
      <ProtectedRoute>{children}</ProtectedRoute>
    </SearchProvider>
  );
}