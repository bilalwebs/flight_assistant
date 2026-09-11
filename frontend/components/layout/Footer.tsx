import Link from "next/link";

const columns = [
  {
    heading: "Product",
    links: [
      { label: "Flights", href: "/flights/search" },
      { label: "AI Assistant", href: "/assistant" },
      { label: "My Bookings", href: "/bookings" },
      { label: "Profile", href: "/profile" },
    ],
  },
  {
    heading: "Account",
    links: [
      { label: "Sign in", href: "/login" },
      { label: "Create account", href: "/register" },
    ],
  },
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white">
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
                Flight Assistant AI
              </span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-6 text-slate-600">
              AI-powered flight discovery and booking assistance.
            </p>
          </div>

          {columns.map((column) => (
            <div key={column.heading}>
              <h2 className="text-sm font-semibold text-foreground">
                {column.heading}
              </h2>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-slate-600 transition-colors hover:text-primary-700"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-slate-200 pt-6">
          <p className="text-sm text-slate-500">
            © {year} Flight Assistant AI
          </p>
        </div>
      </div>
    </footer>
  );
}