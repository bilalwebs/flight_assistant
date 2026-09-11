export function TypingIndicator() {
  return (
    <div
      role="status"
      aria-label="Assistant is thinking"
      className="flex items-center gap-2.5 text-slate-500"
    >
      <span className="flex items-center gap-1" aria-hidden="true">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
            style={{ animationDelay: `${dot * 150}ms` }}
          />
        ))}
      </span>
      <span className="text-xs font-medium">Assistant is thinking…</span>
    </div>
  );
}