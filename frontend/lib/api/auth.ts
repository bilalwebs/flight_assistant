import { apiFetch } from "@/lib/api/api-client";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  UserResponse,
} from "@/lib/types";

/** POST /api/auth/register — public. Returns the created user (no token). */
export function register(input: RegisterRequest): Promise<UserResponse> {
  return apiFetch<UserResponse>("/api/auth/register", {
    method: "POST",
    body: input,
  });
}

/** POST /api/auth/login — public. Returns access token + user. */
export function login(input: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: input,
  });
}

/** GET /api/auth/me — requires a valid bearer token. */
export function getMe(token: string): Promise<UserResponse> {
  return apiFetch<UserResponse>("/api/auth/me", { token });
}