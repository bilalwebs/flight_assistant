"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/api-client";
import { confirmBooking, createBooking } from "@/lib/api/bookings";
import { getFlightDetails } from "@/lib/api/flights";
import { useAuth } from "@/lib/auth/auth-context";
import { useSearch } from "@/lib/search/search-context";
import type { BookingResponse, CreateBookingRequest, Flight } from "@/lib/types";
import { formatCabin, formatFullDate, formatTime } from "@/lib/utils/date";
import {
  MAX_PASSENGERS,
  clampPassengerCount,
  emptyPassenger,
  toPassengerPayload,
  validateContact,
  validatePassenger,
  type ContactFieldErrors,
  type ContactFormValues,
  type PassengerFieldErrors,
  type PassengerFormValues,
} from "@/lib/utils/booking";

import { BookingConfirmation } from "@/components/bookings/BookingConfirmation";
import { BookingReview } from "@/components/bookings/BookingReview";
import { ContactInformation } from "@/components/bookings/ContactInformation";
import { PassengerForm } from "@/components/bookings/PassengerForm";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/LoadingSkeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

type LoadStatus =
  | { kind: "loading" }
  | { kind: "error"; errorKind: "not_found" | "forbidden" | "network" | "server" }
  | { kind: "done" };

type FlowStatus =
  | { kind: "form" }
  | { kind: "creating" }
  | { kind: "pending"; booking: BookingResponse; confirmError?: string | null }
  | { kind: "confirming"; booking: BookingResponse }
  | { kind: "confirmed"; booking: BookingResponse }
  | { kind: "conflict" };

interface FlowError {
  title: string;
  message: string;
}

interface NewBookingFlowProps {
  flightId: string;
}

function classifyLoadError(error: unknown): LoadStatus {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "not_found":
        return { kind: "error", errorKind: "not_found" };
      case "forbidden":
        return { kind: "error", errorKind: "forbidden" };
      case "network":
        return { kind: "error", errorKind: "network" };
      default:
        return { kind: "error", errorKind: "server" };
    }
  }
  return { kind: "error", errorKind: "server" };
}

/** Create-booking failure -> user-facing panel. Returns "conflict" for seat loss. */
function classifyCreateError(error: unknown): FlowError | "conflict" {
  if (error instanceof ApiError) {
    if (error.status === 400 && /insufficient seat|seat\(s\) remaining/i.test(error.message)) {
      return "conflict";
    }
    switch (error.code) {
      case "not_found":
        return {
          title: "Flight not found",
          message: "This flight is no longer bookingable. It may have been removed.",
        };
      case "forbidden":
        return { title: "Access denied", message: "You don't have permission to create this booking." };
      case "bad_request":
      case "validation":
        return { title: "Booking details invalid", message: error.message };
      case "conflict":
        return { title: "Booking conflict", message: "Please refresh and try again." };
      default:
        return {
          title: "Unable to complete your booking right now.",
          message: "We couldn't reach the booking service. Please try again.",
        };
    }
  }
  return {
    title: "Unable to complete your booking right now.",
    message: "Something went wrong. Please try again.",
  };
}

function confirmErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "not_found") return "This booking is no longer available.";
    if (error.code === "forbidden") return "You don't have permission to confirm this booking.";
    if (error.code === "bad_request" || error.code === "conflict") return error.message;
    return "Unable to complete the confirmation right now. Please try again.";
  }
  return "Unable to complete the confirmation right now. Please try again.";
}

const PASSENGER_COUNT_OPTIONS = Array.from({ length: MAX_PASSENGERS }, (_, index) => ({
  value: String(index + 1),
  label: index === 0 ? "1 passenger" : `${index + 1} passengers`,
}));

export function NewBookingFlow({ flightId }: NewBookingFlowProps) {
  const { accessToken, user, handleUnauthorized } = useAuth();
  const { searchParams } = useSearch();

  const [flight, setFlight] = useState<Flight | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>({ kind: "loading" });

  const [passengerCount, setPassengerCount] = useState(() =>
    clampPassengerCount(searchParams.passenger_count),
  );
  const [passengers, setPassengers] = useState<PassengerFormValues[]>(() =>
    Array.from({ length: clampPassengerCount(searchParams.passenger_count) }, () =>
      emptyPassenger(),
    ),
  );
  const [passengerErrors, setPassengerErrors] = useState<(PassengerFieldErrors | null)[]>([]);
  const [contact, setContact] = useState<ContactFormValues>(() => ({
    email: user?.email ?? "",
    phone: user?.phone ?? "",
  }));
  const [contactErrors, setContactErrors] = useState<ContactFieldErrors>({});
  const [showInlineErrors, setShowInlineErrors] = useState(false);

  const [status, setStatus] = useState<FlowStatus>({ kind: "form" });
  const [formError, setFormError] = useState<FlowError | null>(null);

  const loadFlight = useCallback(async () => {
    setLoadStatus({ kind: "loading" });
    try {
      const details = await getFlightDetails(flightId, accessToken ?? "");
      setFlight(details);
      setLoadStatus({ kind: "done" });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return;
      }
      setLoadStatus(classifyLoadError(error));
    }
  }, [flightId, accessToken, handleUnauthorized]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const details = await getFlightDetails(flightId, accessToken ?? "");
        if (!cancelled) {
          setFlight(details);
          setLoadStatus({ kind: "done" });
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 401) {
            handleUnauthorized();
            return;
          }
          setLoadStatus(classifyLoadError(error));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [flightId, accessToken, handleUnauthorized]);

  function handleCountChange(count: number) {
    setPassengerCount(count);
    setPassengers((current) => {
      if (current.length === count) return current;
      const next = current.slice(0, count);
      while (next.length < count) next.push(emptyPassenger());
      return next;
    });
    setPassengerErrors((current) => current.slice(0, count));
  }

  function handlePassengerChange(index: number, next: PassengerFormValues) {
    setPassengers((current) => {
      const copy = current.slice();
      copy[index] = next;
      return copy;
    });
    setPassengerErrors((current) => {
      const copy = current.slice();
      copy[index] = null;
      return copy;
    });
  }

  function handleContactChange(next: ContactFormValues) {
    setContact(next);
    setContactErrors({});
  }

  const handleCreate = useCallback(async () => {
    if (!flight || !accessToken) return;
    if (status.kind === "creating" || status.kind === "confirming") return;

    const passengerErrorList = passengers.map((passenger) => validatePassenger(passenger));
    const anyPassengerErrors = passengerErrorList.some((errors) => Object.keys(errors).length > 0);
    const contactError = validateContact(contact);
    const anyContactErrors = Object.keys(contactError).length > 0;

    if (anyPassengerErrors || anyContactErrors) {
      setPassengerErrors(passengerErrorList);
      setContactErrors(contactError);
      setShowInlineErrors(true);
      return;
    }

    setShowInlineErrors(false);
    setFormError(null);
    setStatus({ kind: "creating" });

    const payload: CreateBookingRequest = {
      flight_id: flight.id,
      passengers: passengers.map(toPassengerPayload),
      cabin_class: flight.cabin_class,
      contact_email: contact.email.trim() || null,
      contact_phone: contact.phone.trim() || null,
    };

    try {
      const booking = await createBooking(payload, accessToken);
      setStatus({ kind: "pending", booking, confirmError: null });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return;
      }
      const classified = classifyCreateError(error);
      if (classified === "conflict") {
        setStatus({ kind: "conflict" });
      } else {
        setFormError(classified);
        setStatus({ kind: "form" });
      }
    }
  }, [flight, accessToken, passengers, contact, status, handleUnauthorized]);

  const handleConfirm = useCallback(async () => {
    if (status.kind !== "pending") return;
    if (!accessToken) return;
    const pending = status.booking;
    setStatus({ kind: "confirming", booking: pending });
    try {
      const updated = await confirmBooking(pending.pnr, accessToken);
      setStatus({ kind: "confirmed", booking: updated });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return;
      }
      setStatus({
        kind: "pending",
        booking: pending,
        confirmError: confirmErrorMessage(error),
      });
    }
  }, [status, accessToken, handleUnauthorized]);

  if (loadStatus.kind === "loading") {
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="space-y-4" role="status" aria-label="Loading booking flow">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  if (loadStatus.kind === "error") {
    const notFound = loadStatus.errorKind === "not_found";
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <ErrorState
          title={notFound ? "Flight or booking not found" : "Unable to load this flight."}
          message={
            notFound
              ? "This flight is no longer bookable or the link is incorrect."
              : loadStatus.errorKind === "forbidden"
                ? "Your account doesn't have access to this flight."
                : "We couldn't load the flight details. Please try again."
          }
          onRetry={notFound ? undefined : () => void loadFlight()}
        />
        {notFound ? (
          <div className="mt-4 flex justify-center">
            <Button variant="outline" size="sm" href="/flights/search">
              Back to Search
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  if (!flight) {
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <ErrorState title="Flight or booking not found" message="This flight is no longer bookable or the link is incorrect." />
      </div>
    );
  }

  // A flight with no remaining seats cannot be booked.
  if (flight.available_seats <= 0 || status.kind === "conflict") {
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <div
          role="alert"
          className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-card"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-700">
            <svg
              aria-hidden="true"
              className="h-6 w-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </span>
          <h1 className="font-heading text-xl font-semibold tracking-tight text-foreground">
            Seats are no longer available for this flight.
          </h1>
          <p className="max-w-sm text-sm text-slate-600">
            This flight has sold out. Choose another flight or refine your search.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="outline" href={`/flights/${flight.id}`}>
              Back to Flight Details
            </Button>
            <Button variant="primary" href="/flights/search">
              Search Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (status.kind === "pending" || status.kind === "confirming" || status.kind === "confirmed") {
    const booking = status.booking;
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <Button variant="ghost" size="sm" href={`/flights/${flightId}`} className="mb-4 -ml-2 text-slate-600">
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
            <path d="m12 19-7-7 7-7" />
            <path d="M19 12H5" />
          </svg>
          Back to Flight
        </Button>
        <BookingConfirmation
          booking={booking}
          flight={flight}
          status={status.kind === "confirmed" ? "confirmed" : "pending"}
          confirming={status.kind === "confirming"}
          confirmError={status.kind === "pending" ? status.confirmError ?? null : null}
          onConfirm={() => void handleConfirm()}
        />
      </div>
    );
  }

  const CTALabel =
    status.kind === "creating"
      ? "Creating booking..."
      : formError
        ? "Try again — Create Booking"
        : "Create Booking";

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <Button
        variant="ghost"
        size="sm"
        href={`/flights/${flightId}`}
        className="mb-4 -ml-2 text-slate-600"
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
          <path d="m12 19-7-7 7-7" />
          <path d="M19 12H5" />
        </svg>
        Back to Flight
      </Button>

      <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-sm font-semibold text-primary-700">
              {flight.airline_code}
            </span>
            <div>
              <p className="font-heading text-lg font-semibold tracking-tight text-foreground">
                {flight.airline} · Flight {flight.flight_number}
              </p>
              <p className="text-sm text-slate-600">
                {flight.origin_city} ({flight.origin}) → {flight.destination_city} (
                {flight.destination})
              </p>
              <p className="mt-0.5 text-sm text-slate-600">
                {formatFullDate(flight.departure_time)} · {formatTime(flight.departure_time)} →{" "}
                {formatTime(flight.arrival_time)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="info">{formatCabin(flight.cabin_class)}</Badge>
            <Badge variant={flight.available_seats > 0 ? "success" : "danger"}>
              {flight.available_seats} seats left
            </Badge>
          </div>
        </div>
      </header>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_26rem] lg:items-start">
        <div className="space-y-6">
          <section
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
            aria-labelledby="passenger-information-heading"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2
                id="passenger-information-heading"
                className="font-heading text-base font-semibold tracking-tight text-foreground"
              >
                Passenger information
              </h2>
              <div className="w-44">
                <Select
                  label="Passengers"
                  options={PASSENGER_COUNT_OPTIONS}
                  value={String(passengerCount)}
                  onChange={(event) => handleCountChange(Number(event.target.value))}
                  disabled={status.kind === "creating"}
                />
              </div>
            </div>
            <div className="mt-4 space-y-4">
              {passengers.map((passenger, index) => (
                <PassengerForm
                  key={index}
                  index={index + 1}
                  value={passenger}
                  errors={passengerErrors[index] ?? undefined}
                  onChange={(next) => handlePassengerChange(index, next)}
                  disabled={status.kind === "creating"}
                />
              ))}
            </div>
          </section>

          <ContactInformation
            value={contact}
            errors={contactErrors}
            onChange={handleContactChange}
            disabled={status.kind === "creating"}
          />
        </div>

        <div className="space-y-4 lg:sticky lg:top-24">
          <BookingReview flight={flight} passengers={passengers} contact={contact} />

          <div
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
            aria-live="polite"
          >
            {formError ? (
              <div
                role="alert"
                className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5"
              >
                <p className="text-sm font-semibold text-red-700">{formError.title}</p>
                <p className="mt-0.5 text-sm text-red-700">{formError.message}</p>
              </div>
            ) : showInlineErrors ? (
              <p role="alert" className="mb-4 text-sm text-red-600">
                Please fix the highlighted fields above before creating your booking.
              </p>
            ) : null}
            <Button
              variant="primary"
              size="lg"
              fullWidth
              loading={status.kind === "creating"}
              disabled={status.kind === "creating"}
              onClick={() => void handleCreate()}
              aria-label="Create booking"
            >
              {CTALabel}
            </Button>
            <p className="mt-3 text-center text-xs text-slate-500">
              By creating you agree to the fare conditions. The final total is
              set by the airline at booking time.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}