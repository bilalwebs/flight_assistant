import type { Metadata } from "next";

import { NewBookingFlow } from "@/components/bookings/NewBookingFlow";

export const metadata: Metadata = {
  title: "Book a Flight | Flight Assistant AI",
  description: "Enter passenger and contact details to book your flight.",
};

interface NewBookingPageProps {
  params: Promise<{ flightId: string }>;
}

export default async function NewBookingPage({
  params,
}: NewBookingPageProps) {
  const { flightId } = await params;
  return <NewBookingFlow flightId={flightId} />;
}