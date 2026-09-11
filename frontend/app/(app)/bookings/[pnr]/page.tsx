import type { Metadata } from "next";

import { BookingDetails } from "@/components/bookings/BookingDetails";

export const metadata: Metadata = {
  title: "Booking Details | Flight Assistant AI",
  description: "View details and manage your flight booking.",
};

interface BookingDetailsPageProps {
  params: Promise<{ pnr: string }>;
}

export default async function BookingDetailsPage({ params }: BookingDetailsPageProps) {
  const { pnr } = await params;
  return <BookingDetails pnr={pnr} />;
}