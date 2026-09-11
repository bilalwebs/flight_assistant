import type { PassengerInfo, PassengerType } from "@/lib/types";

/** Maximum supported passenger count (mirrors the price breakdown UI). */
export const MAX_PASSENGERS = 9;

/** Human labels for the passenger-type selector. */
export const PASSENGER_TYPE_OPTIONS: { value: PassengerType; label: string }[] = [
  { value: "adult", label: "Adult" },
  { value: "child", label: "Child" },
  { value: "infant", label: "Infant" },
];

export const PASSENGER_TYPE_LABELS: Record<PassengerType, string> = {
  adult: "Adult",
  child: "Child",
  infant: "Infant",
};

export interface PassengerFormValues {
  first_name: string;
  last_name: string;
  passenger_type: PassengerType;
  date_of_birth: string;
}

export function emptyPassenger(): PassengerFormValues {
  return {
    first_name: "",
    last_name: "",
    passenger_type: "adult",
    date_of_birth: "",
  };
}

export type PassengerFieldErrors = Partial<
  Record<keyof PassengerFormValues, string>
>;

/** Clamp an arbitrary count to the supported 1..MAX range. */
export function clampPassengerCount(count: number): number {
  if (!Number.isFinite(count)) return 1;
  return Math.min(MAX_PASSENGERS, Math.max(1, Math.trunc(count)));
}

function isReasonableDateOfBirth(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (year < 1900 || year > 2200 || month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }
  const date = new Date(`${value}T00:00:00`);
  if (
    date.getFullYear() !== year ||
    date.getMonth() + 1 !== month ||
    date.getDate() !== day
  ) {
    return false;
  }
  return date.getTime() <= Date.now();
}

/** Backend-compatible passenger validation (service _validate_passenger). */
export function validatePassenger(
  value: PassengerFormValues,
): PassengerFieldErrors {
  const errors: PassengerFieldErrors = {};

  const first = value.first_name.trim();
  const last = value.last_name.trim();

  if (!first) errors.first_name = "First name is required.";
  else if (first.length > 100) errors.first_name = "First name must be 100 characters or fewer.";

  if (!last) errors.last_name = "Last name is required.";
  else if (last.length > 100) errors.last_name = "Last name must be 100 characters or fewer.";

  if (!["adult", "child", "infant"].includes(value.passenger_type)) {
    errors.passenger_type = "Select a valid passenger type.";
  }

  if (!value.date_of_birth) errors.date_of_birth = "Date of birth is required.";
  else if (!isReasonableDateOfBirth(value.date_of_birth)) {
    errors.date_of_birth = "Date of birth must be valid (YYYY-MM-DD) and not in the future.";
  }

  return errors;
}

export interface ContactFormValues {
  email: string;
  phone: string;
}

export type ContactFieldErrors = Partial<Record<keyof ContactFormValues, string>>;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateContact(values: ContactFormValues): ContactFieldErrors {
  const errors: ContactFieldErrors = {};
  const email = values.email.trim();

  if (!email) errors.email = "Contact email is required.";
  else if (!EMAIL_PATTERN.test(email)) errors.email = "Enter a valid email address.";

  const phone = values.phone.trim();
  if (phone && (phone.length > 20 || !/^[+0-9()\-.\s]+$/.test(phone))) {
    errors.phone = "Enter a valid phone number.";
  }

  return errors;
}

/** Convert form values to the exact backend PassengerInfo payload. */
export function toPassengerPayload(value: PassengerFormValues): PassengerInfo {
  return {
    first_name: value.first_name.trim(),
    last_name: value.last_name.trim(),
    passenger_type: value.passenger_type,
    date_of_birth: value.date_of_birth,
  };
}

/** "Adult · John Doe" for the review list. */
export function formatPassengerName(value: PassengerFormValues): string {
  return [value.first_name, value.last_name].map((part) => part.trim()).filter(Boolean).join(" ");
}