"use client";

import { Select } from "@/components/ui/Select";
import { SORT_OPTIONS, type SortKey } from "@/lib/utils/sorting";

interface FlightSortProps {
  value: SortKey;
  onChange: (key: SortKey) => void;
  disabled?: boolean;
}

export function FlightSort({ value, onChange, disabled }: FlightSortProps) {
  return (
    <Select
      label="Sort results"
      options={SORT_OPTIONS}
      value={value}
      onChange={(event) => onChange(event.target.value as SortKey)}
      disabled={disabled}
      className="w-full sm:w-60"
    />
  );
}