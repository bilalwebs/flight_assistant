"use client";

import { useAssistant } from "@/lib/assistant/assistant-context";
import { Button } from "@/components/ui/Button";

import { AssistantEmptyState } from "./AssistantEmptyState";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

export function AssistantShell() {
  const { messages, sendMessage, clearConversation } = useAssistant();

  function handlePrompt(prompt: string) {
    void sendMessage(prompt);
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-4rem)] w-full max-w-5xl flex-col">
      <header className="flex items-center justify-between gap-3 px-4 pb-3 pt-5 sm:px-6 sm:pt-7">
        <div>
          <h1 className="font-heading text-xl font-semibold tracking-tight text-foreground">
            AI Travel Assistant
          </h1>
          <p className="text-sm text-slate-600">
            Ask me about flights, routes, and travel tips.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={clearConversation}
          aria-label="Start a new conversation"
        >
          New conversation
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 sm:px-6 sm:pb-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center">
            <AssistantEmptyState onSelect={handlePrompt} />
          </div>
        ) : (
          <MessageList />
        )}
      </div>

      <ChatInput />
    </div>
  );
}