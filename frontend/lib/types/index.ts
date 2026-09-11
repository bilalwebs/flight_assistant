/**
 * TypeScript types matching the Flight Assistant AI backend API schemas.
 * These mirror `backend/schemas/*.py` exactly — do not add/rename fields.
 */

// --- Authentication (backend/schemas/auth.py) ---

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  phone: string | null;
  membership: string;
  loyalty_points: string;
  is_active: boolean;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  phone?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

/** Data persisted by the frontend for the authenticated session. */
export interface AuthSession {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

// --- Health (backend/main.py GET /api/health) ---

export interface HealthInfo {
  status: string;
  app: string;
  version: string;
  ai_provider?: string;
  model?: string;
}

// --- Flights (backend/schemas/flights.py) ---

export type CabinClass = "economy" | "business";

/** POST /api/flights/search body — mirrors FlightSearchRequest exactly. */
export interface FlightSearchRequest {
  origin: string;
  destination: string;
  /** Departure date, ISO format (sent as YYYY-MM-DD). */
  date: string;
  cabin_class: string;
}

/** Flight response — mirrors FlightResponse exactly. */
export interface Flight {
  id: string;
  flight_number: string;
  airline: string;
  airline_code: string;
  origin: string;
  destination: string;
  origin_city: string;
  destination_city: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  stops: number;
  cabin_class: string;
  base_price: number;
  tax_percent: number;
  available_seats: number;
  total_seats: number;
}

/** Backend-supported time-of-day bucket for the filter API. */
export type TimeOfDay = "morning" | "afternoon" | "evening" | "night";

/** POST /api/flights/filter body — mirrors FlightFilterRequest exactly. */
export interface FlightFilterRequest {
  origin: string;
  destination: string;
  /** Departure date, ISO format (sent as YYYY-MM-DD). */
  date: string;
  cabin_class?: CabinClass;
  max_stops?: number;
  /** Airline name (e.g. "Emirates") — NOT the 2-letter code. */
  airline?: string;
  min_price?: number;
  max_price?: number;
  time_of_day?: TimeOfDay;
}

/** POST /api/flights/price response — mirrors PriceBreakdownResponse exactly. */
export interface PriceBreakdown {
  flight_id: string;
  flight_number: string;
  passenger_count: number;
  base_price_per_person: number;
  tax_per_person: number;
  total_per_person: number;
  grand_total: number;
  currency: string;
}

/** GET /api/flights/{flight_id}/seats response — mirrors SeatAvailabilityResponse exactly. */
export interface SeatAvailability {
  flight_id: string;
  flight_number: string;
  available_seats: number;
  total_seats: number;
}

// --- AI Assistant (backend/schemas/assistant.py) ---

export type AssistantCabinPreference = "economy" | "business" | "first";

/** POST /api/assistant/chat body — mirrors AssistantMessageRequest exactly. */
export interface AssistantMessageRequest {
  message: string;
  conversation_id: string | null;
  origin_preference?: string | null;
  destination_preference?: string | null;
  cabin_preference?: AssistantCabinPreference | null;
}

/** POST /api/assistant/chat response — mirrors AssistantMessageResponse exactly. */
export interface AssistantMessageResponse {
  conversation_id: string;
  message: string;
  success: boolean;
}

// --- Bookings (backend/schemas/bookings.py) ---

/** Passenger type accepted by the booking API. */
export type PassengerType = "adult" | "child" | "infant";

/** Booking lifecycle status as returned by the backend enum. */
export type BookingStatus = "pending" | "confirmed" | "cancelled";

/** One passenger — mirrors PassengerInfo exactly. */
export interface PassengerInfo {
  first_name: string;
  last_name: string;
  passenger_type: PassengerType;
  /** Date of birth, YYYY-MM-DD (required by the booking service). */
  date_of_birth: string;
}

/** POST /api/bookings body — mirrors BookingCreateRequest exactly. */
export interface CreateBookingRequest {
  flight_id: string;
  passengers: PassengerInfo[];
  /** Mirrors the backend: economy | business | first (free string). */
  cabin_class: string;
  /** Defaults to the authenticated user's email on the backend when omitted. */
  contact_email?: string | null;
  contact_phone?: string | null;
}

/** Booking response — mirrors BookingResponse exactly. */
export interface BookingResponse {
  id: string;
  pnr: string;
  user_id: string;
  flight_id: string;
  status: BookingStatus;
  cabin_class: string;
  passenger_count: number;
  base_amount: number;
  tax_amount: number;
  total_amount: number;
  currency: string;
  contact_email: string;
  contact_phone: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** GET /api/bookings response — mirrors BookingListResponse exactly. */
export interface BookingListResponse {
  count: number;
  bookings: BookingResponse[];
}