import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12 sm:px-6">
      <div className="w-full max-w-md">
        <Link
          href="/"
          className="mb-6 flex items-center justify-center gap-2.5"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-soft">
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 2 11 13" />
              <path d="M22 2 15 22l-4-9-9-4Z" />
            </svg>
          </span>
          <span className="font-heading text-base font-semibold tracking-tight text-foreground">
            Flight Assistant <span className="text-primary">AI</span>
          </span>
        </Link>
        {children}
      </div>
    </div>
  );
}