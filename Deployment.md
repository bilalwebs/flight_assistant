# Deployment — Flight Assistant Backend (Phase 9)

Deploys **only the FastAPI backend** to **Render** (one platform). The Next.js
frontend is intentionally not deployed; it will be wired up in **Phase 10**
(origin added to `ALLOWED_ORIGINS`).

## Platform choice

| | Render | Railway |
| --- | --- | --- |
| Docker support | ✅ native | ✅ native |
| `render.yaml` Blueprint (as-code) | ✅ `preDeployCommand` for migrations | config in `railway.json` |
| Pre-deploy migration hook | ✅ supported | requires a separate `prebuild` script |
| Free tier | ✅ web service (sleeps when idle) | pilot plan required |
| Health checks | ✅ `/api/health` | manual |

**Selected: Render** — Docker web service, Blueprint-as-code deploys the container
with `preDeployCommand: alembic upgrade head`, a `/api/health` check, and secret
env vars set in the dashboard (`sync: false`).

## Architecture

```
Browser (Phase 10 frontend, https)
   └── HTTPS
        └── Render web service — flight-assistant-backend
             │  Docker image built from ./backend (uv-locked deps)
             │  CMD: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}   (no --reload)
             │  preDeploy: python -m alembic upgrade head   (Alembic owns schema)
             └── DATABASE_URL → Neon PostgreSQL (postgresql+asyncpg, TLS)
                                   schema at revision 133b5978bcff
```

- **Database** — Neon PostgreSQL. Schema is managed **exclusively by Alembic**
  (app startup `init_db()` is a no-op for PostgreSQL). Seed data runs **manually
  and explicitly only** — never automatically.
- **Assistant sessions** — `sessions.db` writes to the container's ephemeral
  disk (`SESSION_DB_PATH`); ephemeral on the free plan (survives redeploys only
  if a Render disk is attached). Operational data is unaffected.
- **HTTPS** — terminates at Render (public `https://…` URL). App binds
  `0.0.0.0:$PORT` behind it.

## Production start command

```text
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- no `--reload`
- binds `0.0.0.0`
- respects the platform-injected `PORT` env var

## Environment variables (names only — values live in Render secrets)

| Env var | Secret | Required | Source / note |
| --- | --- | --- | --- |
| `ENVIRONMENT` | no | yes | `production` (enables fail-fast validators) |
| `DATABASE_URL` | **yes** | yes | Neon PostgreSQL URL — set in dashboard |
| `JWT_SECRET_KEY` | **yes** | yes | strong, ≥ 32 chars — set in dashboard |
| `ALLOWED_ORIGINS` | no | yes | explicit origins; Phase 10 adds frontend origin |
| `GEMINI_API_KEY` | **yes** | if Gemini | provider key — set in dashboard |
| `GROQ_API_KEY` | **yes** | if Groq | provider key — set in dashboard |
| `DEFAULT_PROVIDER` | no | no | `gemini` (default) |
| `DISABLE_TRACING` | no | no | `true` (default) |
| `SESSION_DB_PATH` | no | no | default `./sessions.db` |
| `APP_NAME` / `APP_VERSION` | no | no | service metadata |
| `PORT` | no | no | Render injects; fallback 8000 |

Production fail-fast guards (already verified in Phase 8) refuse to start if:
PostgreSQL is not `postgresql+asyncpg`, the JWT secret is weak, CORS is
`*`/empty, or `DEBUG` is true.

## Manual steps (Render dashboard)

> This machine had no Render/Railway CLI and no authenticated platform tooling,
> so the deploy must be finished by hand. All artifacts below are ready.

1. **Push** the current `main` branch to GitHub (`bilalwebs/flight_assistant`).
2. In [Render](https://render.com) → **New → Blueprint** → connect that repo —
   Render reads `render.yaml` and creates `flight-assistant-backend`.
3. In the service → **Environment**, set the secret values (from your private
   `backend/.env`, never printed here):
   - `DATABASE_URL` = your Neon connection string
   - `JWT_SECRET_KEY` = a fresh strong secret (≥ 32 chars)
   - `ALLOWED_ORIGINS` = `http://localhost:3000` for now
   - `GEMINI_API_KEY` / `GROQ_API_KEY` = provider keys
4. **Manual Deploy** the service. The deploy log must show:
   - `pre-deploy` step: `alembic upgrade head` → `INFO  [alembic] Running upgrade` → `dict object` / reaches `133b5978bcff`
   - app start: `uvicorn … --host 0.0.0.0 --port …` — **no** `--reload`
   - health check succeeding against `/api/health`
5. Verify the **public URL**:
   - `GET https://<service>.onrender.com/` → 200, `"status": "online"`
   - `GET https://<service>.onrender.com/api/health` → 200, `"status": "ok"`
6. Review **Logs** for errors (warnings about deprecations are pre-existing).

## Database

- Alembic revision expected: **`133b5978bcff`** (head; no new migration in Phase 9).
- Neon already contains the canonical dataset:
  `flights = 153`, `demo_users = 3`, `families = 13`, and **zero** bookings,
  passengers, and payments. Verify read-only after deploy:
  ```powershell
  $env:ENVIRONMENT = "production"; uv run alembic current   # from backend\
  ```
  and a read-only count query through the app engine.
- **Neon pooler robustness** — the app engine connects with
  `statement_cache_size=0` for PostgreSQL (asyncpg's default prepared-statement
  cache is unsafe behind Neon's PgBouncer pooled connections; verified read-only
  against Neon that this removes intermittent `DBAPIError`s).
- Seeding is **explicit only** — run once, deliberately, and never from startup:
  ```powershell
  uv run python -m database.run_init_seed
  ```
  `seed_database()` is idempotent (skips when `flights` already has rows).

## Local image build (this machine)

The Windows Docker engine was not operational during Phase 9, so the container
build/run is a manual step here (on any Docker-capable machine):

```bash
docker build -t flight-assistant-backend ./backend
docker run --rm -p 8100:8000 \
  --env ENVIRONMENT=production \
  --env DATABASE_URL='postgresql+asyncpg://…' \
  --env JWT_SECRET_KEY='…≥32 chars…' \
  --env ALLOWED_ORIGINS='http://localhost:3000' \
  --env GEMINI_API_KEY='…' \
  flight-assistant-backend
curl -s http://127.0.0.1:8100/api/health
```

## Notes / limitations

- Free Render web services **sleep after ~15 min idle** and cold-start on the
  next request — fine for this portfolio deployment.
- `sessions.db` (assistant memory) is ephemeral unless a Render disk is added;
  this does not touch flight/booking data.
- Stripe env vars are left blank → payments endpoints return `503` (inert), as by design.