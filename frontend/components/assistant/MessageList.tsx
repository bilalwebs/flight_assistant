"use client";

import { useEffect, useRef } from "react";

import { useAssistant } from "@/lib/assistant/assistant-context";

import { MessageBubble } from "./MessageBubble";

export function MessageList() {
  const { messages, retry } = useAssistant();
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, retry]);

  return (
    <div aria-label="Conversation messages" className="flex flex-col gap-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onRetry={retry}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}