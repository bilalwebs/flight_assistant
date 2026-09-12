# Vercel Deployment — Flight Assistant AI Backend

Status: **Vercel deployment READY — actual deployment still pending.**

This backend deploys to Vercel on the native Python (FastAPI) runtime as a single
Vercel Function (Fluid compute). No business logic, agents, models, or database
configuration were changed for Vercel. The existing Render configuration
(`render.yaml`, `backend/Dockerfile`, `backend/.dockerignore`, `Deployment.md`)
is untouched and remains a valid fallback.

## Required Vercel configuration (already in repo)

- `backend/pyproject.toml` → `[tool.vercel] entrypoint = "main:app"` (pins detection)
- `backend/vercel.json` → `functions.main.py.maxDuration = 60` and `excludeFiles`
  (tests, `.env*`, `*.db*`, report files are excluded from the function bundle)

## Vercel dashboard configuration

- Project Root Directory: `backend` (the FastAPI project lives at `backend/main.py`).
- Framework preset: FastAPI (single function routed to all paths).
- Deploy method: Git integration (push triggers deploy) or `vercel --prod`.

## Environment variables (set in Vercel dashboard — values are secrets)

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `<Neon PostgreSQL URL - secret>` |
| `JWT_SECRET_KEY` | `<strong secret, minimum 32 characters>` |
| `ALLOWED_ORIGINS` | `<temporary frontend/local origin, e.g. http://localhost:3000>` |
| `DEFAULT_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | `<secret>` |
| `GROQ_API_KEY` | `<secret, only if using Groq>` |
| `DISABLE_TRACING` | `True` |
| `SESSION_DB_PATH` | `/tmp/sessions.db` |
| `APP_NAME` | `Flight Assistant AI` |
| `APP_VERSION` | `1.0.0` |

Notes:

- `PORT` is **not** required — Vercel Functions do not require the app to bind a port.
- `TEST_DATABASE_URL` must **not** be configured in production.
- The module-level model/agent initialization requires the active provider key
  (`GEMINI_API_KEY` by default) to be set or the function will fail to import.
- After the Next.js frontend is deployed, change `ALLOWED_ORIGINS` to the actual
  frontend Vercel URL. The backend stays environment-driven — no URL is hardcoded.

## Session storage limitation (accepted for this phase)

The Vercel root filesystem is read-only. `SESSION_DB_PATH` must therefore point to
`/tmp/sessions.db` on Vercel. That filesystem is **ephemeral and per-instance**, so
assistant conversation memory may be lost after cold starts or when requests reach
different instances. Do **not** hardcode `/tmp/sessions.db` into Python code; it is
set only via the environment variable. Durable, PostgreSQL-backed session storage is
a future phase and is out of scope here.

## Alembic / database

- No migration changes were made. Current migration head: `133b5978bcff`.
- Alembic must **not** run automatically during application startup (Vercel has no
  pre-deploy command). The operator verifies/runs the migration manually against
  Neon before production traffic if required:

  ```
  uv run alembic upgrade head
  ```

- The current Neon database is already at head, so this should be a no-op.
- Never run `create_all()`, `drop_all()`, or seeds against Neon.

## Manual deployment steps

1. Confirm baseline: `uv run python -m pytest` (12 passed) in `backend/`.
2. Connect the repo in Vercel; set Root Directory to `backend`.
3. Set the environment variables above (never commit secrets).
4. Operator: verify Neon is at head via `uv run alembic current` / `upgrade head`.
5. Deploy. Verify public URLs return 200: `GET /` and `GET /api/health`.
6. (Later) Update `ALLOWED_ORIGINS` to the deployed frontend origin.