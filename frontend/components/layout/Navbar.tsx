"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/utils/cn";

import { Button } from "@/components/ui/Button";

interface NavigationItem {
  label: string;
  href: string;
}

function navigation(isAuthenticated: boolean): NavigationItem[] {
  if (!isAuthenticated) return [];
  return [
    { label: "Flights", href: "/flights/search" },
    { label: "AI Assistant", href: "/assistant" },
    { label: "My Bookings", href: "/bookings" },
  ];
}

function isActive(pathname: string, href: string): boolean {
  if (pathname === href || pathname.startsWith(`${href}/`)) return true;
  // A flight detail page (/flights/<id>) belongs to the Flights section.
  if (href === "/flights/search" && pathname.startsWith("/flights/")) return true;
  // Creating a booking for a flight is part of the Flights journey.
  if (href === "/flights/search" && pathname.startsWith("/bookings/new/")) return true;
  return false;
}

function displayName(name: string, email: string): string {
  const first = name.trim().split(/\s+/)[0];
  return first || email;
}

export function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const { isAuthenticated, user, logout } = useAuth();
  const links = navigation(isAuthenticated);

  const email = user?.email ?? "";
  const signedInName = user ? displayName(user.name, email) : email;

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  function handleLogout() {
    logout();
    setOpen(false);
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-background/85 backdrop-blur">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
      >
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-lg focus-visible:outline-none"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-soft">
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 2 11 13" />
              <path d="M22 2 15 22l-4-9-9-4Z" />
            </svg>
          </span>
          <span className="font-heading text-base font-semibold tracking-tight text-foreground">
            Flight Assistant{" "}
            <span className="text-primary">AI</span>
          </span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-lg px-3.5 py-2 text-sm font-medium transition-colors",
                isActive(pathname, item.href)
                  ? "bg-primary-50 text-primary-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          {isAuthenticated ? (
            <>
              <span
                className="max-w-40 truncate text-sm text-slate-600"
                title={user?.email}
              >
                {signedInName}
              </span>
              <Button variant="ghost" size="sm" href="/profile">
                Profile
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                aria-label="Sign out"
              >
                Logout
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" href="/login">
                Login
              </Button>
              <Button variant="primary" size="sm" href="/register">
                Get Started
              </Button>
            </>
          )}
        </div>

        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-slate-700 transition-colors hover:bg-slate-100 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((current) => !current)}
        >
          {open ? (
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          ) : (
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 6h16" />
              <path d="M4 12h16" />
              <path d="M4 18h16" />
            </svg>
          )}
        </button>
      </nav>

      {open ? (
        <div
          id="mobile-menu"
          className="animate-scale-in border-t border-slate-200 bg-background px-4 pb-5 pt-3 md:hidden"
        >
          {links.length > 0 ? (
            <div className="flex flex-col gap-1">
              {links.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive(pathname, item.href)
                      ? "bg-primary-50 text-primary-700"
                      : "text-slate-700 hover:bg-slate-100",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          ) : null}

          <div className="mt-3 border-t border-slate-200 pt-4">
            {isAuthenticated ? (
              <div className="flex flex-col gap-2">
                <p className="px-1 text-sm text-slate-600">
                  Signed in as{" "}
                  <span className="font-medium text-slate-800" title={user?.email}>
                    {signedInName}
                  </span>
                </p>
                <div className="flex flex-col gap-2">
                  <Button
                    variant="outline"
                    size="md"
                    href="/profile"
                    onClick={() => setOpen(false)}
                  >
                    Profile
                  </Button>
                  <Button variant="danger" size="md" onClick={handleLogout}>
                    Logout
                  </Button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="md"
                  href="/login"
                  onClick={() => setOpen(false)}
                >
                  Login
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  href="/register"
                  onClick={() => setOpen(false)}
                >
                  Get Started
                </Button>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </header>
  );
}