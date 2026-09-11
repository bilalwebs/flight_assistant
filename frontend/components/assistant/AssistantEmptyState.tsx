import { SuggestedPrompts } from "./SuggestedPrompts";

interface AssistantEmptyStateProps {
  onSelect: (prompt: string) => void;
}

export function AssistantEmptyState({ onSelect }: AssistantEmptyStateProps) {
  return (
    <div className="flex w-full flex-col items-center gap-5 px-2 py-8 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
        <svg
          aria-hidden="true"
          className="h-7 w-7"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      </span>
      <div className="flex flex-col items-center gap-1.5">
        <h2 className="font-heading text-lg font-semibold text-foreground">
          How can I help you travel?
        </h2>
        <p className="max-w-md text-sm text-slate-600">
          I can search flights between cities, compare your options, look up a
          specific flight by its number, and answer general travel questions.
        </p>
      </div>
      <SuggestedPrompts onSelect={onSelect} />
    </div>
  );
}