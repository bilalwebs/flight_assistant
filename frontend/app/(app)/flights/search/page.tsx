import type { Metadata } from "next";

import { FlightSearchBoard } from "@/components/flights/FlightSearchBoard";

export const metadata: Metadata = {
  title: "Flight Search | Flight Assistant AI",
  description: "Search available flights and compare your options.",
};

export default function FlightSearchPage() {
  return <FlightSearchBoard />;
}