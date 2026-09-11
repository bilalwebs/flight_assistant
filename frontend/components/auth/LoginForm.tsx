"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api/api-client";
import { useAuth } from "@/lib/auth/auth-context";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface FormErrors {
  email?: string;
  password?: string;
  form?: string;
}

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const registered = searchParams.get("registered") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const nextErrors: FormErrors = {};
    if (!email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!email.includes("@")) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (!password) {
      nextErrors.password = "Password is required.";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!validate()) return;

    setSubmitting(true);
    setErrors({});

    try {
      await login({ email: email.trim().toLowerCase(), password });
      router.push(next ?? "/flights/search");
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          setErrors({ form: "Invalid email or password." });
        } else if (error.status === 403) {
          setErrors({ form: "This account is not active." });
        } else if (error.code === "network" || error.status === 0) {
          setErrors({
            form: "We couldn't connect to the server. Please try again.",
          });
        } else {
          setErrors({ form: error.message });
        }
      } else {
        setErrors({ form: "Something went wrong. Please try again." });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
      <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">
        Welcome back
      </h1>
      <p className="mt-1.5 text-sm text-slate-600">
        Sign in to continue your journey.
      </p>

      {registered ? (
        <p
          className="mt-4 rounded-lg bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800"
          role="status"
        >
          Your account was created. Sign in to continue.
        </p>
      ) : null}

      {errors.form ? (
        <p
          className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700"
          role="alert"
        >
          {errors.form}
        </p>
      ) : null}

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={errors.email}
          required
        />
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          placeholder="Your password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.password}
          required
        />

        <Button
          type="submit"
          size="lg"
          loading={submitting}
          className="mt-2 w-full"
          disabled={submitting}
        >
          {submitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium text-primary-600 underline-offset-2 hover:underline"
        >
          Create one
        </Link>
      </p>

      <p className="mt-4 text-center text-sm">
        <Link
          href="/"
          className="text-slate-500 underline-offset-2 hover:text-slate-700 hover:underline"
        >
          Back to home
        </Link>
      </p>
    </div>
  );
}