# Flight Assistant AI — Frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind client for the Flight Assistant AI platform.

## Getting Started

1. Start the backend (see `../README.md` — FastAPI on `http://127.0.0.1:8000`).
2. (Optional) copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL`.
3. Install dependencies and run:

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Scripts

| Script        | Purpose                        |
| ------------- | ------------------------------ |
| `npm run dev` | Start the dev server           |
| `npm run build` | Production build             |
| `npm run start` | Serve the production build  |
| `npm run lint` | ESLint over the codebase     |

Type checking: `npx tsc --noEmit`.

## Structure

- `app/` — App Router pages and route groups (`(app)` is the authenticated area behind `ProtectedRoute`).
- `components/` — UI, feedback, layout, flight, booking, and layout components.
- `lib/` — API client (`apiFetch`), per-domain API modules, auth context, search/assistant contexts, shared types and date/currency helpers.
- `tests/` — E2E harnesses (Node + Chrome DevTools Protocol) documented in the root `README.md`.

## Configuration

The only environment variable is `NEXT_PUBLIC_API_URL` (backend base URL, public). No secrets belong in the frontend. See `../README.md` for full setup and testing documentation.