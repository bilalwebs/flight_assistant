import type { HealthInfo } from "@/lib/types";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? DEFAULT_API_URL;

type ErrorDetailItem = { loc?: (string | number)[]; msg?: string; type?: string };

function statusCodeToMessage(status: number): string {
  switch (status) {
    case 400:
      return "The request was invalid.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return "The requested resource was not found.";
    case 409:
      return "A conflict occurred. Please try something else.";
    case 422:
      return "Some of the information provided is invalid.";
    default:
      return "Something went wrong. Please try again.";
  }
}

/** Normalized, frontend-friendly error thrown by the API client. */
export class ApiError extends Error {
  readonly status: number;
  readonly code:
    | "network"
    | "bad_request"
    | "unauthorized"
    | "forbidden"
    | "not_found"
    | "conflict"
    | "validation"
    | "server"
    | "unknown";
  readonly fieldErrors?: Record<string, string>;

  constructor(
    message: string,
    options: {
      status: number;
      code?: ApiError["code"];
      fieldErrors?: Record<string, string>;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? guessCode(options.status);
    this.fieldErrors = options.fieldErrors;
  }
}

function guessCode(status: number): ApiError["code"] {
  switch (status) {
    case 0:
      return "network";
    case 400:
      return "bad_request";
    case 401:
      return "unauthorized";
    case 403:
      return "forbidden";
    case 404:
      return "not_found";
    case 409:
      return "conflict";
    case 422:
      return "validation";
    default:
      return status >= 500 ? "server" : "unknown";
  }
}

/**
 * First error message (and a flat field→message map) from a FastAPI 422 body,
 * e.g. `{"detail": [{"loc": ["body", "email"], "msg": "...", ...}]}`.
 */
function parseErrorEnvelope(data: unknown): {
  message: string;
  fieldErrors?: Record<string, string>;
} {
  if (typeof data === "object" && data !== null) {
    const record = data as Record<string, unknown>;
    const detail = record.detail;

    if (typeof detail === "string" && detail.length > 0) {
      return { message: detail };
    }

    if (Array.isArray(detail)) {
      const fieldErrors: Record<string, string> = {};
      let firstMessage = "";
      for (const item of detail as ErrorDetailItem[]) {
        const field = Array.isArray(item.loc)
          ? String(item.loc[item.loc.length - 1] ?? "form")
          : "form";
        const msg =
          item.msg && typeof item.msg === "string"
            ? item.msg.replace(/^Value error, /, "")
            : "Invalid value.";
        if (!fieldErrors[field]) fieldErrors[field] = msg;
        if (!firstMessage) firstMessage = msg;
      }
      return {
        message: firstMessage || "Some of the information provided is invalid.",
        fieldErrors,
      };
    }
  }
  return { message: statusCodeToMessage(500) };
}

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
}

/**
 * Typed JSON request wrapper around the Flight Assistant backend.
 *
 * - Prefixed with NEXT_PUBLIC_API_URL
 * - Attaches `Authorization: Bearer <token>` when a token is supplied
 * - Parses the backend error envelope (`{"detail": "..."}` or a 422 list)
 *   into a normalized ApiError
 * - Throws ApiError on non-2xx and on network failure (status 0)
 */
export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = "GET", body, token, signal } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      signal,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === "AbortError";
    throw new ApiError(
      aborted ? "The request timed out. Please try again." : "We couldn't connect to the server. Please try again.",
      { status: 0, code: "network" },
    );
  }

  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    const { message, fieldErrors } = parseErrorEnvelope(data);
    const fallback = fieldErrors ? message : statusCodeToMessage(response.status);
    throw new ApiError(message || fallback, {
      status: response.status,
      fieldErrors,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * Calls GET {API_BASE_URL}/api/health and returns the backend health info.
 * Never throws: any network/parse/timeout failure returns null so callers
 * can render a graceful "offline" state instead of crashing the page.
 */
export async function getHealth(timeoutMs = 5000): Promise<HealthInfo | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await apiFetch<HealthInfo>("/api/health", { signal: controller.signal });
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}