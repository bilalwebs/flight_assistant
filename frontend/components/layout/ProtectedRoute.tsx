"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth/auth-context";

import { ErrorState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/LoadingSkeleton";

function RouteLoading() {
  return (
    <div
      className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6"
      role="status"
      aria-label="Checking your session"
    >
      <div className="flex flex-col gap-4">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
        <div className="mt-4 flex flex-col gap-3">
          <Skeleton className="h-16 w-full rounded-2xl" />
          <Skeleton className="h-16 w-full rounded-2xl" />
          <Skeleton className="h-16 w-full rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

function BlockedAccount() {
  return (
    <div className="mx-auto w-full max-w-xl px-4 py-16 sm:px-6">
      <ErrorState
        title="Account access denied"
        message="Your account is not active. Please contact support for help."
      />
    </div>
  );
}

/**
 * Guards pages that require an authenticated session.
 *
 * - While the stored session is validated, shows a loading state so
 *   protected content never flashes before auth is known.
 * - Unauthenticated visitors are redirected to /login?next=<current path>.
 * - A 403 (inactive/blocked account) renders an account-access error.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, accountBlocked } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !accountBlocked && !isAuthenticated) {
      const next = encodeURIComponent(pathname ?? "/");
      router.replace(`/login?next=${next}`);
    }
  }, [isLoading, accountBlocked, isAuthenticated, pathname, router]);

  if (isLoading) {
    return <RouteLoading />;
  }

  if (accountBlocked) {
    return <BlockedAccount />;
  }

  if (!isAuthenticated) {
    return null; // The redirect effect above will take the user to /login.
  }

  return <>{children}</>;
}