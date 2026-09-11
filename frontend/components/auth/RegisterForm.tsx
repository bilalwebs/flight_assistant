"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api/api-client";
import { useAuth } from "@/lib/auth/auth-context";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface FormErrors {
  name?: string;
  email?: string;
  phone?: string;
  password?: string;
  confirmPassword?: string;
  form?: string;
}

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const nextErrors: FormErrors = {};
    if (!name.trim()) {
      nextErrors.name = "Name is required.";
    }
    if (!email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!email.includes("@")) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (!password) {
      nextErrors.password = "Password is required.";
    } else if (password.length < 8) {
      nextErrors.password = "Password must be at least 8 characters.";
    }
    if (confirmPassword !== password) {
      nextErrors.confirmPassword = "Passwords don't match.";
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
      const result = await register({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        phone: phone.trim() || null,
      });

      if (result.autoLoggedIn) {
        router.push(next ?? "/flights/search");
      } else {
        router.push("/login?registered=1");
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          setErrors({ form: "An account with this email already exists." });
        } else if (error.code === "network" || error.status === 0) {
          setErrors({ form: "We couldn't connect to the server. Please try again." });
        } else if (error.status === 422) {
          const fieldErrors = error.fieldErrors ?? {};
          const fieldEntry = Object.entries(fieldErrors).filter(([field]) =>
            ["name", "email", "password"].includes(field),
          );
          if (fieldEntry.length > 0) {
            setErrors(
              Object.fromEntries(fieldEntry) as Pick<FormErrors, "name" | "email" | "password">,
            );
          } else {
            setErrors({ form: error.message || "Check your details and try again." });
          }
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
        Create your account
      </h1>
      <p className="mt-1.5 text-sm text-slate-600">
        Join Flight Assistant AI to search flights and manage bookings.
      </p>

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
          label="Full name"
          type="text"
          autoComplete="name"
          placeholder="Jane Smith"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={errors.name}
          required
        />
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
          label="Phone (optional)"
          type="tel"
          autoComplete="tel"
          placeholder="+1 555 000 0000"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          error={errors.phone}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.password}
          required
        />
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          placeholder="Repeat your password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={errors.confirmPassword}
          required
        />

        <Button
          type="submit"
          size="lg"
          loading={submitting}
          className="mt-2 w-full"
          disabled={submitting}
        >
          {submitting ? "Creating account..." : "Create account"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-medium text-primary-600 underline-offset-2 hover:underline"
        >
          Sign in
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