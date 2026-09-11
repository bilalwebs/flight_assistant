"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/api/api-client";
import { getMe, login as apiLogin, register as apiRegister } from "@/lib/api/auth";
import type {
  AuthSession,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  UserResponse,
} from "@/lib/types";

const STORAGE_KEY = "flight_assistant_auth";

function readStoredSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (
      typeof parsed.access_token === "string" &&
      parsed.access_token.length > 0 &&
      parsed.user &&
      typeof parsed.user === "object"
    ) {
      return parsed as AuthSession;
    }
    return null;
  } catch {
    return null;
  }
}

function writeStoredSession(session: AuthSession): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Storage unavailable (private mode, quota, blocked) — session lives in memory only.
  }
}

function clearStoredSession(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore — nothing else we can do.
  }
}

interface AuthContextValue {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  /** True while the stored session is being validated against /api/auth/me. */
  isLoading: boolean;
  /** True when /me returned 403 (account inactive/blocked). */
  accountBlocked: boolean;
  login: (input: LoginRequest) => Promise<LoginResponse>;
  register: (input: RegisterRequest) => Promise<{ autoLoggedIn: boolean }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  /** Hard-closes the session after any 401, used at data boundaries. */
  handleUnauthorized: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accountBlocked, setAccountBlocked] = useState(false);

  const clearSession = useCallback(() => {
    clearStoredSession();
    setSession(null);
    setAccountBlocked(false);
  }, []);

  // Hydrate once on mount: restore from localStorage, then trust /me.
  useEffect(() => {
    let cancelled = false;

    Promise.resolve(readStoredSession())
      .then((stored) => {
        if (cancelled) return;

        if (!stored) {
          setIsLoading(false);
          return;
        }

        setSession(stored);

        return getMe(stored.access_token)
          .then((user) => {
            if (cancelled) return;
            setSession((current) =>
              current && current.access_token === stored.access_token
                ? { ...current, user }
                : current,
            );
          })
          .catch((error) => {
            if (cancelled) return;
            if (error instanceof ApiError) {
              if (error.status === 401) {
                clearSession();
                return;
              }
              if (error.status === 403) {
                clearStoredSession();
                setSession(null);
                setAccountBlocked(true);
                return;
              }
            }
            // Network/server failure: keep the stored session intact — the
            // server is authoritative, but we never silently corrupt what
            // we saved.
          })
          .finally(() => {
            if (!cancelled) setIsLoading(false);
          });
      });

    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (input: LoginRequest) => {
    const response = await apiLogin(input);
    const nextSession: AuthSession = {
      access_token: response.access_token,
      token_type: response.token_type,
      expires_in: response.expires_in,
      user: response.user,
    };
    writeStoredSession(nextSession);
    setAccountBlocked(false);
    setSession(nextSession);
    return response;
  }, []);

  const register = useCallback(async (input: RegisterRequest) => {
    await apiRegister(input);

    // Register returns UserResponse without a token. Sign the user in with the
    // real login endpoint using the credentials they just created.
    try {
      const response = await apiLogin({ email: input.email, password: input.password });
      const nextSession: AuthSession = {
        access_token: response.access_token,
        token_type: response.token_type,
        expires_in: response.expires_in,
        user: response.user,
      };
      writeStoredSession(nextSession);
      setAccountBlocked(false);
      setSession(nextSession);
      return { autoLoggedIn: true };
    } catch {
      clearStoredSession();
      setSession(null);
      return { autoLoggedIn: false };
    }
  }, []);

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const refreshUser = useCallback(async () => {
    if (!session) return;
    try {
      const user = await getMe(session.access_token);
      setSession((current) => (current ? { ...current, user } : current));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
      } else if (error instanceof ApiError && error.status === 403) {
        clearStoredSession();
        setSession(null);
        setAccountBlocked(true);
      }
    }
  }, [session, clearSession]);

  const handleUnauthorized = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      accessToken: session?.access_token ?? null,
      isAuthenticated: session !== null,
      isLoading,
      accountBlocked,
      login,
      register,
      logout,
      refreshUser,
      handleUnauthorized,
    }),
    [session, isLoading, accountBlocked, login, register, logout, refreshUser, handleUnauthorized],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}