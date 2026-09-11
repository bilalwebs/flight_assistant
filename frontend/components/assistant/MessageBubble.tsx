import type { AssistantChatMessage } from "@/lib/assistant/assistant-context";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils/cn";

import { TypingIndicator } from "./TypingIndicator";

interface MessageBubbleProps {
  message: AssistantChatMessage;
  onRetry: () => void;
}

export function MessageBubble({ message, onRetry }: MessageBubbleProps) {
  if (message.pending && message.role === "assistant") {
    return (
      <div className="flex justify-start">
        <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-card">
          <TypingIndicator />
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <p
          className={cn(
            "max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-3 text-sm leading-relaxed text-white",
          )}
        >
          {message.content}
        </p>
      </div>
    );
  }

  if (message.error) {
    return (
      <div className="flex justify-start">
        <div
          role="alert"
          className="flex max-w-[85%] flex-col gap-2.5 rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 px-4 py-3"
        >
          <p className="text-sm leading-relaxed text-red-700">
            {message.error.text}
          </p>
          <div>
            <Button variant="outline" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm leading-relaxed text-foreground shadow-card">
        {message.content}
      </p>
    </div>
  );
}