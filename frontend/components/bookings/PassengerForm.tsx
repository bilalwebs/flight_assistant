"use client";

import { todayISO } from "@/lib/utils/date";
import type {
  PassengerFieldErrors,
  PassengerFormValues,
} from "@/lib/utils/booking";
import { PASSENGER_TYPE_OPTIONS } from "@/lib/utils/booking";

import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

interface PassengerFormProps {
  /** 1-based passenger number used in labels/aria. */
  index: number;
  value: PassengerFormValues;
  errors?: PassengerFieldErrors;
  onChange: (next: PassengerFormValues) => void;
  disabled?: boolean;
}

const TYPE_OPTIONS = PASSENGER_TYPE_OPTIONS.map((option) => ({
  value: option.value,
  label: option.label,
}));

export function PassengerForm({
  index,
  value,
  errors = {},
  onChange,
  disabled = false,
}: PassengerFormProps) {
  const title = `Passenger ${index}`;

  return (
    <fieldset
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      disabled={disabled}
      aria-label={title}
    >
      <legend className="px-1 font-heading text-sm font-semibold tracking-tight text-foreground">
        {title}
      </legend>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Select
            id={`passenger-${index}-type`}
            label="Passenger type"
            options={TYPE_OPTIONS}
            value={value.passenger_type}
            onChange={(event) =>
              onChange({
                ...value,
                passenger_type: event.target.value as PassengerFormValues["passenger_type"],
              })
            }
            error={errors.passenger_type}
            required
          />
        </div>
        <Input
          id={`passenger-${index}-first-name`}
          label="First name"
          value={value.first_name}
          onChange={(event) => onChange({ ...value, first_name: event.target.value })}
          error={errors.first_name}
          autoComplete="given-name"
          required
          disabled={disabled}
        />
        <Input
          id={`passenger-${index}-last-name`}
          label="Last name"
          value={value.last_name}
          onChange={(event) => onChange({ ...value, last_name: event.target.value })}
          error={errors.last_name}
          autoComplete="family-name"
          required
          disabled={disabled}
        />
        <Input
          id={`passenger-${index}-dob`}
          label="Date of birth"
          type="date"
          max={todayISO()}
          value={value.date_of_birth}
          onChange={(event) => onChange({ ...value, date_of_birth: event.target.value })}
          error={errors.date_of_birth}
          required
          disabled={disabled}
        />
      </div>
    </fieldset>
  );
}