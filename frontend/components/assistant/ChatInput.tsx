"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { useAssistant } from "@/lib/assistant/assistant-context";

import { Button } from "@/components/ui/Button";

export function ChatInput() {
  const { sendMessage, isLoading } = useAssistant();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmed = value.trim();
  const canSend = trimmed.length > 0 && !isLoading;

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 144)}px`;
  }, [value]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) submit();
    }
  }

  function submit() {
    const text = value.trim();
    if (!text || isLoading) return;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    void sendMessage(text);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-slate-200 bg-background p-4 sm:p-5"
    >
      <div className="flex w-full max-w-3xl items-end gap-2 px-4 sm:px-2">
        <label htmlFor="assistant-chat-input" className="sr-only">
          Your message to the travel assistant
        </label>
        <textarea
          id="assistant-chat-input"
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about flights, routes, or travel tips…"
          className="max-h-36 min-h-11 flex-1 resize-none rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-foreground placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40"
        />
        <Button
          type="submit"
          size="md"
          aria-label="Send message"
          disabled={!canSend}
          className="h-11 shrink-0 px-4"
        >
          <svg
            aria-hidden="true"
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M3.4 20.4l17.45-7.48a1 1 0 0 0 0-1.84L3.4 3.6a.993.993 0 0 0-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z" />
          </svg>
          <span className="sr-only">Send message</span>
        </Button>
      </div>
    </form>
  );
}