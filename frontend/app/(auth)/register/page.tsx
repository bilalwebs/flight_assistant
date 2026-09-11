import type { Metadata } from "next";
import { Suspense } from "react";

import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Create account | Flight Assistant AI",
  description: "Create a Flight Assistant AI account.",
};

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8"
          role="status"
        >
          <div className="h-7 w-40 animate-pulse rounded bg-slate-200" />
          <div className="mt-4 space-y-3">
            <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
            <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
            <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
            <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
          </div>
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}