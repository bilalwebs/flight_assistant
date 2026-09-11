"use client";

import { useAuth } from "@/lib/auth/auth-context";
import { formatFullDate } from "@/lib/utils/date";

import { EmptyState } from "@/components/feedback/EmptyState";
import { Skeleton } from "@/components/feedback/LoadingSkeleton";
import { Badge } from "@/components/ui/Badge";

const membershipLabels: Record<string, string> = {
  standard: "Standard",
  silver: "Silver",
  gold: "Gold",
  platinum: "Platinum",
};

export function ProfileView() {
  const { user, isLoading, accountBlocked } = useAuth();

  if (isLoading) {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-5 px-4 py-12 sm:px-6 lg:px-8">
        <Skeleton className="h-8 w-40 rounded-lg" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    );
  }

  if (!user || accountBlocked) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          title="Sign in to view your profile"
          description="Your account details will appear here once you sign in."
        />
      </div>
    );
  }

  const membershipLabel = membershipLabels[user.membership] ?? user.membership;

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">
          Profile
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Your account details with Flight Assistant AI.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
        <div className="border-b border-slate-100 bg-slate-50 px-6 py-5">
          <div className="flex items-center gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-sm font-semibold text-white">
              {user.name.trim().charAt(0).toUpperCase() || "U"}
            </span>
            <div>
              <h2 className="font-heading text-lg font-semibold text-foreground">
                {user.name}
              </h2>
              <p className="text-sm text-slate-600">{user.email}</p>
            </div>
          </div>
        </div>

        <dl className="divide-y divide-slate-100 px-6">
          <div className="flex items-center justify-between py-4">
            <dt className="text-sm text-slate-600">Membership</dt>
            <dd className="flex items-center gap-2 text-sm font-medium text-foreground">
              {membershipLabel}
              <Badge variant="info">{user.membership}</Badge>
            </dd>
          </div>
          <div className="flex items-center justify-between py-4">
            <dt className="text-sm text-slate-600">Loyalty points</dt>
            <dd className="text-sm font-semibold text-foreground">
              {user.loyalty_points}
            </dd>
          </div>
          <div className="flex items-center justify-between py-4">
            <dt className="text-sm text-slate-600">Phone</dt>
            <dd className="text-sm text-foreground">{user.phone || "—"}</dd>
          </div>
          <div className="flex items-center justify-between py-4">
            <dt className="text-sm text-slate-600">Member since</dt>
            <dd className="text-sm text-foreground">
              {user.created_at ? formatFullDate(user.created_at) : "—"}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}