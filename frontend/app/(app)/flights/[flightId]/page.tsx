import type { Metadata } from "next";

import { FlightDetails } from "@/components/flights/FlightDetails";

export const metadata: Metadata = {
  title: "Flight Details | Flight Assistant AI",
  description: "View flight schedule, price breakdown, and seat availability.",
};

interface FlightDetailsPageProps {
  params: Promise<{ flightId: string }>;
}

export default async function FlightDetailsPage({
  params,
}: FlightDetailsPageProps) {
  const { flightId } = await params;
  return <FlightDetails flightId={flightId} />;
}