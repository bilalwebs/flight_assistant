import { cn } from "@/lib/utils/cn";

interface SkeletonProps {
  className?: string;
}

/** Base animated placeholder block. */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      data-testid="skeleton"
      className={cn("animate-pulse rounded-lg bg-slate-200/80", className)}
    />
  );
}

/** Generic text-lines skeleton that holds stable layout space. */
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-4 w-1/2" />
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} className="h-4 w-full" />
      ))}
    </div>
  );
}

/** Card-style skeleton with image slot, rows, and action slot. */
export function SkeletonCard() {
  return (
    <div
      className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      role="status"
      aria-label="Loading content"
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <SkeletonText lines={2} />
      <div className="flex items-center justify-between">
        <Skeleton className="h-9 w-28 rounded-lg" />
        <Skeleton className="h-9 w-24 rounded-lg" />
      </div>
    </div>
  );
}

/** Loading skeleton usage for lists of cards. */
export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: count }, (_, index) => (
        <SkeletonCard key={index} />
      ))}
    </div>
  );
}