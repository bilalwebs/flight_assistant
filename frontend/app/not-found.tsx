import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/feedback/EmptyState";

export default function NotFound() {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-24 sm:px-6 lg:px-8">
      <EmptyState
        title="Page not found"
        description="The page you're looking for doesn't exist or has moved."
        action={
          <Button href="/" className="mt-1">
            Back to home
          </Button>
        }
      />
    </div>
  );
}