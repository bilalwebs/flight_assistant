"use client";

import type {
  ContactFieldErrors,
  ContactFormValues,
} from "@/lib/utils/booking";

import { Input } from "@/components/ui/Input";

interface ContactInformationProps {
  value: ContactFormValues;
  errors?: ContactFieldErrors;
  onChange: (next: ContactFormValues) => void;
  disabled?: boolean;
}

export function ContactInformation({
  value,
  errors = {},
  onChange,
  disabled = false,
}: ContactInformationProps) {
  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      aria-labelledby="contact-information-heading"
    >
      <h2
        id="contact-information-heading"
        className="font-heading text-base font-semibold tracking-tight text-foreground"
      >
        Contact information
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        We&apos;ll send the booking confirmation to this email address.
      </p>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
          id="contact-email"
          label="Contact email"
          type="email"
          value={value.email}
          onChange={(event) => onChange({ ...value, email: event.target.value })}
          error={errors.email}
          autoComplete="email"
          placeholder="you@example.com"
          required
          disabled={disabled}
        />
        <Input
          id="contact-phone"
          label="Contact phone"
          type="tel"
          value={value.phone}
          onChange={(event) => onChange({ ...value, phone: event.target.value })}
          error={errors.phone}
          autoComplete="tel"
          placeholder="+1 555 123 4567"
          helperText="Optional"
          disabled={disabled}
        />
      </div>
    </section>
  );
}