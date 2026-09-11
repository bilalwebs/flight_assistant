"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api/api-client";
import { cn } from "@/lib/utils/cn";

type Status = "checking" | "online" | "offline";

const statusConfig: Record<
  Status,
  { label: string; dotClass: string; textClass: string }
> = {
  checking: {
    label: "Checking backend...",
    dotClass: "bg-amber-400",
    textClass: "text-slate-500",
  },
  online: {
    label: "Backend Online",
    dotClass: "bg-emerald-500",
    textClass: "text-emerald-700",
  },
  offline: {
    label: "Backend Offline",
    dotClass: "bg-red-500",
    textClass: "text-red-600",
  },
};

export function SystemStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [check, setCheck] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setStatus("checking");
      const health = await getHealth();
      if (cancelled) return;
      setStatus(health && health.status === "ok" ? "online" : "offline");
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [check]);

  const config = statusConfig[status];

  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium shadow-sm"
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2" aria-hidden="true">
        {status === "checking" ? (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400" />
        ) : null}
        <span className={cn("relative h-2 w-2 rounded-full", config.dotClass)} />
      </span>
      <span className={config.textClass}>{config.label}</span>
      {status === "offline" ? (
        <button
          type="button"
          onClick={() => setCheck((current) => current + 1)}
          className="ml-1 font-semibold text-primary-600 underline-offset-2 transition-colors hover:text-primary-700 hover:underline"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}