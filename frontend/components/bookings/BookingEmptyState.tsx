import { EmptyState } from "@/components/feedback/EmptyState";
import { Button } from "@/components/ui/Button";

interface BookingEmptyStateProps {
  onBrowse?: () => void;
}

export function BookingEmptyState({ onBrowse }: BookingEmptyStateProps) {
  return (
    <EmptyState
      title="No bookings yet"
      description="When you book a flight, your bookings will appear here. Search for a flight to get started."
      action={
        <Button variant="primary" size="sm" href="/flights/search" onClick={onBrowse}>
          Search flights
        </Button>
      }
    />
  );
}