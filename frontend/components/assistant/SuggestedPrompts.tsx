const SUGGESTED_PROMPTS = [
  "Find me flights from Karachi to Dubai tomorrow",
  "What flights go from Karachi to Istanbul on Friday?",
  "Tell me about flight EK-601",
  "What's the difference between nonstop and connecting flights?",
];

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

export function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  return (
    <div className="flex flex-col items-center gap-2.5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        Try asking
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect(prompt)}
            className="rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm text-slate-700 transition-colors hover:border-primary-400 hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}