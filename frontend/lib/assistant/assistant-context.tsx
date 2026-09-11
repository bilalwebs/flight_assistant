"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/api/api-client";
import { sendAssistantMessage } from "@/lib/api/assistant";
import { useAuth } from "@/lib/auth/auth-context";

export type AssistantRole = "user" | "assistant";

export type AssistantMessageErrorKind =
  | "network"
  | "validation"
  | "forbidden"
  | "unauthorized"
  | "server"
  | "unknown";

export interface AssistantMessageError {
  kind: AssistantMessageErrorKind;
  text: string;
}

export interface AssistantChatMessage {
  id: string;
  role: AssistantRole;
  content: string;
  /** True while the backend is working on this assistant reply. */
  pending?: boolean;
  /** Set when the last turn failed; the reply can be retried. */
  error?: AssistantMessageError | null;
}

interface AssistantContextValue {
  messages: AssistantChatMessage[];
  /** Conversation id returned by the backend; sent back to preserve memory. */
  conversationId: string | null;
  isLoading: boolean;
  sendMessage: (text: string) => Promise<void>;
  retry: () => Promise<void>;
  clearConversation: () => void;
}

const AssistantContext = createContext<AssistantContextValue | undefined>(undefined);

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function toAssistantError(error: unknown): AssistantMessageError {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "network":
        return {
          kind: "network",
          text: "Unable to reach the travel assistant. Please check your connection and try again.",
        };
      case "unauthorized":
        return {
          kind: "unauthorized",
          text: "Your session has expired. Please sign in again.",
        };
      case "forbidden":
        return {
          kind: "forbidden",
          text: "You don't have permission to use the travel assistant right now.",
        };
      case "validation":
        return {
          kind: "validation",
          text: error.message || "That message couldn't be sent. Please try rephrasing it.",
        };
      case "server":
        return {
          kind: "server",
          text: "The travel assistant is temporarily unavailable. Please try again in a moment.",
        };
      default:
        break;
    }
  }
  return {
    kind: "unknown",
    text: "Something went wrong while contacting the travel assistant. Please try again.",
  };
}

export function AssistantProvider({ children }: { children: ReactNode }) {
  const { accessToken, handleUnauthorized } = useAuth();

  const [messages, setMessages] = useState<AssistantChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Backend turns are serialized: one active turn at a time. The ref lets us
  // ignore stale responses after "New conversation" clears state mid-flight.
  const activeTurnRef = useRef<{ userText: string } | null>(null);
  const lastFailedTextRef = useRef<string | null>(null);

  const runTurn = useCallback(
    async (text: string, mode: "send" | "retry") => {
      if (activeTurnRef.current) return;
      activeTurnRef.current = { userText: text };
      setIsLoading(true);

      if (mode === "send") {
        setMessages((current) => [
          ...current,
          { id: makeId(), role: "user", content: text },
          { id: makeId(), role: "assistant", content: "", pending: true },
        ]);
      } else {
        // Retry reuses the failed assistant bubble — the user message is kept.
        setMessages((current) =>
          current.map((m) =>
            m.role === "assistant" && m.error
              ? { ...m, content: "", pending: true, error: null }
              : m,
          ),
        );
      }

      try {
        const response = await sendAssistantMessage(
          { message: text, conversation_id: conversationId },
          accessToken ?? "",
        );
        if (!activeTurnRef.current || activeTurnRef.current.userText !== text) return;

        setConversationId(response.conversation_id);
        lastFailedTextRef.current = null;
        setMessages((current) =>
          current.map((m) =>
            m.role === "assistant" && m.pending
              ? { ...m, pending: false, content: response.message }
              : m,
          ),
        );
      } catch (error) {
        if (!activeTurnRef.current || activeTurnRef.current.userText !== text) return;

        const assistantError = toAssistantError(error);
        lastFailedTextRef.current = text;
        setMessages((current) =>
          current.map((m) =>
            m.role === "assistant" && m.pending
              ? { ...m, pending: false, error: assistantError }
              : m,
          ),
        );

        if (error instanceof ApiError && error.code === "unauthorized") {
          handleUnauthorized();
        }
      } finally {
        if (activeTurnRef.current && activeTurnRef.current.userText === text) {
          activeTurnRef.current = null;
          setIsLoading(false);
        }
      }
    },
    [accessToken, conversationId, handleUnauthorized],
  );

  const sendMessage = useCallback(
    (text: string) => runTurn(text, "send"),
    [runTurn],
  );

  const retry = useCallback(() => {
    const failedText = lastFailedTextRef.current;
    if (!failedText) return Promise.resolve();
    return runTurn(failedText, "retry").catch(() => undefined);
  }, [runTurn]);

  const clearConversation = useCallback(() => {
    activeTurnRef.current = null;
    lastFailedTextRef.current = null;
    setConversationId(null);
    setMessages([]);
    setIsLoading(false);
  }, []);

  const value = useMemo<AssistantContextValue>(
    () => ({
      messages,
      conversationId,
      isLoading,
      sendMessage,
      retry,
      clearConversation,
    }),
    [messages, conversationId, isLoading, sendMessage, retry, clearConversation],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantContextValue {
  const context = useContext(AssistantContext);
  if (context === undefined) {
    throw new Error("useAssistant must be used within an AssistantProvider");
  }
  return context;
}