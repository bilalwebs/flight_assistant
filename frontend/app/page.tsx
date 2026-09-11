import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { SystemStatus } from "@/components/SystemStatus";

interface IconProps {
  className?: string;
}

function SearchIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

function SparklesIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3 14.5 9.5 21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" />
      <path d="M19 3v4" />
      <path d="M21 5h-4" />
    </svg>
  );
}

function CalendarIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="18" height="18" x="3" y="4" rx="2" />
      <path d="M8 2v4" />
      <path d="M16 2v4" />
      <path d="M3 10h18" />
    </svg>
  );
}

function UsersIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function CheckIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function ArrowRightIcon({ className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

interface Feature {
  icon: ReactNode;
  title: string;
  description: string;
}

const features: Feature[] = [
  {
    icon: <SearchIcon className="h-5 w-5" />,
    title: "Smart Flight Search",
    description:
      "Search available flights between cities and compare real options quickly.",
  },
  {
    icon: <SparklesIcon className="h-5 w-5" />,
    title: "AI Travel Assistant",
    description:
      "Get conversational booking help and smart recommendations while you plan.",
  },
  {
    icon: <UsersIcon className="h-5 w-5" />,
    title: "Simple Booking",
    description:
      "Create bookings and manage passenger details and itineraries in one place.",
  },
  {
    icon: <CalendarIcon className="h-5 w-5" />,
    title: "Real-time Availability",
    description:
      "See seat availability and clear pricing straight from the booking system.",
  },
];

const trustPoints = [
  "Flight discovery",
  "Smart recommendations",
  "Booking management",
  "AI assistance",
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[480px] bg-[radial-gradient(60%_50%_at_50%_0%,rgba(76,95,213,0.12),transparent)]"
        />
        <div className="relative mx-auto flex w-full max-w-7xl flex-col items-center px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24 lg:px-8">
          <div className="animate-fade-up">
            <Badge variant="info">AI-powered flight booking platform</Badge>
          </div>

          <h1
            className="animate-fade-up mt-6 max-w-3xl font-heading text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl"
            style={{ animationDelay: "0.08s" }}
          >
            Find your next flight, effortlessly.
          </h1>

          <p
            className="animate-fade-up mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg"
            style={{ animationDelay: "0.16s" }}
          >
            Search flights, compare options, and get intelligent travel
            assistance in one place.
          </p>

          <div
            className="animate-fade-up mt-8 flex w-full flex-col items-center justify-center gap-3 sm:w-auto sm:flex-row"
            style={{ animationDelay: "0.24s" }}
          >
            <Button size="lg" href="/flights/search" className="w-full sm:w-auto">
              Search Flights
              <ArrowRightIcon className="h-4 w-4" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              href="/assistant"
              className="w-full sm:w-auto"
            >
              <SparklesIcon className="h-4 w-4 text-primary-500" />
              Ask AI Assistant
            </Button>
          </div>

          {/* Search preview */}
          <div
            className="animate-fade-up mt-14 w-full max-w-5xl"
            style={{ animationDelay: "0.32s" }}
          >
            <div className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-card sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-heading text-sm font-semibold text-foreground">
                    Smart flight search
                  </span>
                  <Badge variant="default">Preview</Badge>
                </div>
                <p className="text-xs text-slate-500">
                  Sign in to search live flights
                </p>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                <Input
                  label="From"
                  value="Karachi (KHI)"
                  disabled
                  readOnly
                />
                <Input label="To" value="Dubai (DXB)" disabled readOnly />
                <Input label="Departure" value="Tomorrow" disabled readOnly />
                <Select
                  label="Passengers"
                  value="1"
                  disabled
                  options={[
                    { value: "1", label: "1 Passenger" },
                    { value: "2", label: "2 Passengers" },
                    { value: "3", label: "3 Passengers" },
                  ]}
                />
                <Select
                  label="Cabin"
                  value="economy"
                  disabled
                  options={[
                    { value: "economy", label: "Economy" },
                    { value: "business", label: "Business" },
                  ]}
                />
              </div>

              <div className="mt-5 flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center">
                <p className="text-xs leading-5 text-slate-500">
                  This preview shows the search experience. Sign in and start
                  searching to see live availability and pricing.
                </p>
                <Button href="/flights/search" className="w-full sm:w-auto">
                  Search Flights
                  <ArrowRightIcon className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto w-full max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Everything you need to plan a trip
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            A focused set of tools for finding flights, getting help, and
            managing bookings — designed around how people actually travel.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-primary-600 transition-colors group-hover:bg-primary-100">
                {feature.icon}
              </span>
              <h3 className="mt-5 font-heading text-base font-semibold text-foreground">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* AI Assistant CTA */}
      <section className="mx-auto w-full max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-primary-600 px-6 py-14 text-center shadow-card sm:px-12 sm:py-16">
          <div
            aria-hidden="true"
            className="absolute inset-x-0 top-0 h-full bg-[radial-gradient(70%_60%_at_50%_0%,rgba(255,255,255,0.14),transparent)]"
          />
          <div className="relative">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-white">
              <SparklesIcon className="h-6 w-6" />
            </span>
            <h2 className="mt-6 font-heading text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Planning a trip?
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-base leading-7 text-primary-100">
              Let our AI travel assistant help you find the right flight.
            </p>
            <Button
              size="lg"
              variant="outline"
              href="/assistant"
              className="mt-8 border-white/30 bg-white/10 text-white hover:border-white hover:bg-white/20 hover:text-white"
            >
              <SparklesIcon className="h-4 w-4" />
              Try AI Assistant
            </Button>
          </div>
        </div>
      </section>

      {/* Trust / product */}
      <section className="mx-auto w-full max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-10 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-xl">
            <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
              Built for a smoother travel experience
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-600">
              From the first search to a confirmed booking, everything is
              designed to keep your plans moving forward — with a capable AI
              assistant ready when you need a hand.
            </p>
            <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {trustPoints.map((point) => (
                <li
                  key={point}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-50 text-primary-600">
                    <CheckIcon className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-sm font-medium text-slate-800">
                    {point}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="shrink-0">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
              <h3 className="text-sm font-semibold text-foreground">
                System status
              </h3>
              <p className="mt-1 max-w-[220px] text-xs leading-5 text-slate-500">
                Flight data and the AI assistant are powered by the Flight
                Assistant API.
              </p>
              <div className="mt-4">
                <SystemStatus />
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}