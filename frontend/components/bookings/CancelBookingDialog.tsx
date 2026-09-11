import { useEffect, useRef } from "react";

import type { BookingResponse } from "@/lib/types";

import { Button } from "@/components/ui/Button";

interface CancelBookingDialogProps {
  open: boolean;
  booking: BookingResponse | null;
  submitting: boolean;
  errorMessage: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

function focusableSelector(): string {
  return [
    "button:not([disabled])",
    "a[href]",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
  ].join(", ");
}

export function CancelBookingDialog({
  open,
  booking,
  submitting,
  errorMessage,
  onConfirm,
  onClose,
}: CancelBookingDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    previousFocusRef.current =
      (document.activeElement as HTMLElement | null) ?? null;
    // Move focus into the dialog panel when it opens.
    panelRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;

      const panel = panelRef.current;
      const focusable = Array.from(
        panel.querySelectorAll<HTMLElement>(focusableSelector()),
      ).filter((element) => element.offsetParent !== null);

      if (focusable.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first || active === panel || !active || !panel.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last || !panel.contains(active)) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      // Restore focus to the element that opened the dialog.
      previousFocusRef.current?.focus?.();
      previousFocusRef.current = null;
    };
  }, [open, onClose]);

  if (!open || !booking) return null;

  return (
    <div
      aria-modal="true"
      role="dialog"
      aria-label="Cancel booking"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-card focus:outline-none"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="font-heading text-lg font-semibold text-foreground">
          Cancel booking?
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          You are about to cancel booking{" "}
          <span className="font-mono font-semibold tracking-wide text-foreground">
            {booking.pnr}
          </span>
          . This will release {booking.passenger_count} reserved{" "}
          {booking.passenger_count === 1 ? "seat" : "seats"} and cannot be undone.
        </p>

        {errorMessage ? (
          <p
            role="alert"
            className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {errorMessage}
          </p>
        ) : null}

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            size="sm"
            disabled={submitting}
            onClick={onClose}
          >
            Keep booking
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={submitting}
            disabled={submitting}
            onClick={onConfirm}
            aria-label="Confirm cancellation"
          >
            {submitting ? "Cancelling…" : "Cancel booking"}
          </Button>
        </div>
      </div>
    </div>
  );
}