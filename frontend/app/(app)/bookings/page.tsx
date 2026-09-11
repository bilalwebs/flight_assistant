import type { Metadata } from "next";

import { BookingList } from "@/components/bookings/BookingList";

export const metadata: Metadata = {
  title: "My Bookings | Flight Assistant AI",
  description: "View and manage your flight bookings.",
};

export default function BookingsPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">
            My Bookings
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            View and manage your flight reservations.
          </p>
        </div>
      </div>
      <BookingList />
    </div>
  );
}