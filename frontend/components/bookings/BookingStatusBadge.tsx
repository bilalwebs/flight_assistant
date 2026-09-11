import type { BookingStatus } from "@/lib/types";

import { Badge } from "@/components/ui/Badge";

interface BookingStatusBadgeProps {
  status: BookingStatus;
}

const CONFIG: Record<
  BookingStatus,
  { variant: "default" | "success" | "warning" | "danger" | "info"; label: string }
> = {
  pending: { variant: "warning", label: "Pending" },
  confirmed: { variant: "success", label: "Confirmed" },
  cancelled: { variant: "danger", label: "Cancelled" },
};

export function BookingStatusBadge({ status }: BookingStatusBadgeProps) {
  const { variant, label } = CONFIG[status] ?? CONFIG.pending;
  return <Badge variant={variant}>{label}</Badge>;
}