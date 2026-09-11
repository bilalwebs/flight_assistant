import { apiFetch } from "@/lib/api/api-client";
import type {
  AssistantMessageRequest,
  AssistantMessageResponse,
} from "@/lib/types";

/**
 * POST /api/assistant/chat — requires a valid bearer token.
 * `accessToken` is attached by apiFetch as `Authorization: Bearer <token>`.
 *
 * The backend responds with a plain-text assistant message plus a
 * conversation_id that must be sent back on the next message to preserve
 * conversation memory.
 */
export function sendAssistantMessage(
  input: AssistantMessageRequest,
  accessToken: string,
): Promise<AssistantMessageResponse> {
  return apiFetch<AssistantMessageResponse>("/api/assistant/chat", {
    method: "POST",
    body: input,
    token: accessToken,
  });
}