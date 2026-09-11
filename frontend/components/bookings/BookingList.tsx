"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { listMyBookings } from "@/lib/api/bookings";
import { getFlightDetails } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import type { BookingResponse, Flight } from "@/lib/types";

import { BookingCard } from "@/components/bookings/BookingCard";
import { BookingEmptyState } from "@/components/bookings/BookingEmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton";

interface BookingListProps {
  onAddFlight?: () => void;
}

export function BookingList({ onAddFlight }: BookingListProps) {
  const { accessToken, handleUnauthorized } = useAuth();
  const [bookings, setBookings] = useState<BookingResponse[]>([]);
  const [flights, setFlights] = useState<Record<string, Flight>>({});
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const response = await listMyBookings(accessToken);
      const userBookings = response.bookings;
      setBookings(userBookings);

      const ids = Array.from(
        new Set(userBookings.map((b) => b.flight_id)),
      );
      const loaded = await Promise.all(
        ids.map(async (id) => {
          try {
            const flight = await getFlightDetails(id, accessToken);
            return [id, flight] as const;
          } catch {
            return null;
          }
        }),
      );
      setFlights(
        Object.fromEntries(
          loaded.filter(
            (entry): entry is readonly [string, Flight] => entry !== null,
          ),
        ),
      );
      setLoading(false);
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.status === 401) {
          handleUnauthorized();
          return;
        }
        setError(caught);
      } else {
        setError(
          new ApiError("Something went wrong. Please try again.", {
            status: 0,
            code: "unknown",
          }),
        );
      }
      setLoading(false);
    }
  }, [accessToken, handleUnauthorized]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await listMyBookings(accessToken ?? "");
        if (cancelled) return;
        const userBookings = response.bookings;
        setBookings(userBookings);

        const ids = Array.from(
          new Set(userBookings.map((b) => b.flight_id)),
        );
        const loaded = await Promise.all(
          ids.map(async (id) => {
            try {
              const flight = await getFlightDetails(id, accessToken ?? "");
              return [id, flight] as const;
            } catch {
              return null;
            }
          }),
        );
        if (!cancelled) {
          setFlights(
            Object.fromEntries(
              loaded.filter(
                (entry): entry is readonly [string, Flight] => entry !== null,
              ),
            ),
          );
          setLoading(false);
        }
      } catch (caught) {
        if (cancelled) return;
        if (caught instanceof ApiError) {
          if (caught.status === 401) {
            handleUnauthorized();
            return;
          }
          setError(caught);
        } else {
          setError(
            new ApiError("Something went wrong. Please try again.", {
              status: 0,
              code: "unknown",
            }),
          );
        }
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accessToken, handleUnauthorized]);

  if (loading) {
    return <LoadingSkeleton count={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title={error.status === 404 ? "No bookings found" : "Couldn't load your bookings"}
        message={
          error.status === 401
            ? "Your session has expired. Please sign in again."
            : error.message
        }
        onRetry={error.status !== 401 ? () => void load() : undefined}
      />
    );
  }

  if (bookings.length === 0) {
    return <BookingEmptyState onBrowse={onAddFlight} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {bookings.map((booking) => (
        <BookingCard
          key={booking.id}
          booking={booking}
          flight={flights[booking.flight_id] ?? null}
        />
      ))}
    </div>
  );
}