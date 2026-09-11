import { useId, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
}

export function Input({
  label,
  error,
  helperText,
  required = false,
  id,
  className,
  disabled,
  ...props
}: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-slate-800"
        >
          {label}
          {required && (
            <span aria-hidden="true" className="ml-0.5 text-red-500">
              *
            </span>
          )}
        </label>
      </div>
      <input
        id={inputId}
        className={cn(
          "w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-foreground shadow-sm transition-colors placeholder:text-slate-400",
          "focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40",
          "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500",
          error
            ? "border-red-400 focus:border-red-500 focus:ring-red-500/40"
            : "border-slate-300",
          className,
        )}
        required={required}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : helperText ? helperId : undefined}
        {...props}
      />
      {error ? (
        <p id={errorId} className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : helperText ? (
        <p id={helperId} className="text-sm text-slate-500">
          {helperText}
        </p>
      ) : null}
    </div>
  );
}