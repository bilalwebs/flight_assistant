import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Sign in | Flight Assistant AI",
  description: "Sign in to your Flight Assistant AI account.",
};

export default function LoginPage() {
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
            <div className="h-12 w-full animate-pulse rounded-lg bg-slate-200" />
          </div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}