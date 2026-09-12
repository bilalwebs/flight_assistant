"""
Centralized application configuration (python-decouple).

Environment separation (Phase 8):
    development  — local SQLite (flight_assistant.db), permissive defaults
    testing      — isolated temporary SQLite via TEST_DATABASE_URL
    production   — Neon PostgreSQL via DATABASE_URL (postgresql+asyncpg),

                    gated with fail-fast validation: strong JWT secret,
                    explicit CORS origins, no DEBUG, PostgreSQL-only database.

OS environment variables always win over the .env file, so operators can point
Docker/Alembic/tests at the right database with a single variable.
"""
from decouple import config

# ──────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────
VALID_ENVIRONMENTS = ("development", "testing", "production")

ENVIRONMENT = config("ENVIRONMENT", default="development").strip().lower()
if ENVIRONMENT not in VALID_ENVIRONMENTS:
    raise RuntimeError(
        f"ENVIRONMENT must be one of {', '.join(VALID_ENVIRONMENTS)}; got an unsupported value."
    )

IS_PRODUCTION = ENVIRONMENT == "production"

# ──────────────────────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────────────────────
APP_NAME = config("APP_NAME", default="Flight Assistant AI")
APP_VERSION = config("APP_VERSION", default="1.0.0")
DEBUG = config("DEBUG", default=False, cast=bool)

# ──────────────────────────────────────────────────────────────
# CORS (comma-separated explicit origins)
# ──────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [o.strip() for o in config(
    "ALLOWED_ORIGINS", default="http://localhost:3000"
).split(",") if o.strip()]


# ──────────────────────────────────────────────────────────────
# Database
# Local default: async SQLite (aiosqlite). Production (Neon/PostgreSQL) is
# supplied via the DATABASE_URL environment variable, never hardcoded here —
# e.g. postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
# ──────────────────────────────────────────────────────────────

def _strip_psycopg2_query_params(url: str) -> str:
    """Drop psycopg2-only query params (sslmode, channel_binding).

    The asyncpg driver negotiates TLS by default, and the psycopg2 query-style
    options are not valid asyncpg/SQLAlchemy connect arguments.
    """
    header, sep, query = url.partition("?")
    if not sep:
        return url
    kept = [
        param for param in query.split("&")
        if param and param.split("=", 1)[0].strip().lower() not in ("sslmode", "channel_binding")
    ]
    return header + (f"?{'&'.join(kept)}" if kept else "")


def normalize_database_url(raw: str) -> str:
    """Normalize a configured database URL into an async-SQLAlchemy URL.

    Accepts any scheme the operator may have configured:
      - postgresql://...        (psycopg2-style)      -> postgresql+asyncpg://...
      - postgres://...          (alias)               -> postgresql+asyncpg://...
      - postgresql+asyncpg://...                      -> unchanged (params sanitized)
      - sqlite+aiosqlite:///... (local development)    -> unchanged
    """
    url = raw.strip()
    if url.lower().startswith(("postgresql://", "postgres://")):
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]
    if url.lower().startswith("postgresql+asyncpg://"):
        url = _strip_psycopg2_query_params(url)
    return url


DATABASE_URL = normalize_database_url(
    config("DATABASE_URL", default="sqlite+aiosqlite:///./flight_assistant.db")
)

# Optional override used ONLY by the automated test stack. When set, the app's
# engine/session factory bind to this isolated SQLite temp file instead of
# DATABASE_URL — tests never touch the dev database or production/Neon.
# Guarded in database.database: it must be SQLite and must not match DATABASE_URL.
TEST_DATABASE_URL = config("TEST_DATABASE_URL", default="")


def validate_production_db_url(url: str, test_url: str) -> None:
    """Fail fast when production is not pointed at PostgreSQL+asyncpg."""
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "Production must configure a PostgreSQL+asyncpg DATABASE_URL "
            "(postgresql+asyncpg://...). SQLite is local-development only "
            "and is never used in production."
        )
    if test_url and test_url == url:
        raise RuntimeError(
            "Production DATABASE_URL must not equal TEST_DATABASE_URL."
        )


# ──────────────────────────────────────────────────────────────
# Authentication / JWT
# ──────────────────────────────────────────────────────────────
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = config("JWT_EXPIRATION_HOURS", default=24, cast=int)

_WEAK_JWT_SECRETS = {
    "",
    "your-secret-key-change-in-production",
    "replace-with-a-long-random-secret",
    "replace-me",
    "change-me",
    "changeme",
    "secret",
    "secret-key",
}


def validate_jwt_secret(secret: str, environment: str) -> None:
    """Fail fast in production when the JWT secret is missing or obviously weak."""
    if environment != "production":
        return
    if not secret or secret in _WEAK_JWT_SECRETS or len(secret) < 32:
        raise RuntimeError(
            "Production requires a strong JWT_SECRET_KEY (at least 32 characters). "
            "Refusing to start with a missing, default, or obviously weak secret."
        )


def validate_cors_origins(origins: list[str], environment: str) -> None:
    """Fail fast in production when CORS would silently allow any origin."""
    if environment != "production":
        return
    cleaned = [o.strip() for o in origins if o.strip()]
    if not cleaned or any(o == "*" for o in cleaned):
        raise RuntimeError(
            "Production CORS must list explicit origins. A wildcard '*' origin "
            "is not allowed when authentication/credentials are used."
        )


# ──────────────────────────────────────────────────────────────
# Production fail-fast validation.
# Local development and the test stack keep their permissive defaults; only a
# production ENVIRONMENT flips these guards on.
# ──────────────────────────────────────────────────────────────
if IS_PRODUCTION:
    validate_production_db_url(DATABASE_URL, TEST_DATABASE_URL)
    validate_jwt_secret(JWT_SECRET_KEY, ENVIRONMENT)
    validate_cors_origins(ALLOWED_ORIGINS, ENVIRONMENT)
    if DEBUG:
        raise RuntimeError("Refusing to run production with DEBUG=true.")

# ──────────────────────────────────────────────────────────────
# AI Provider
# ──────────────────────────────────────────────────────────────
DEFAULT_PROVIDER = config("DEFAULT_PROVIDER", default="gemini")

# Gemini
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL_NAME = config("GEMINI_MODEL", default="gemini-3.5-flash-lite")

# Groq
GROQ_API_KEY = config("GROQ_API_KEY", default="")
GROQ_BASE_URL = config("GROQ_BASE_URL", default="https://api.groq.com/openai/v1")
GROQ_MODEL_NAME = config("GROQ_MODEL", default="llama3-8b-8192")

# Sessions
SESSION_DB_PATH = config("SESSION_DB_PATH", default="./sessions.db")

# Tracing
DISABLE_TRACING = config("DISABLE_TRACING", default=True, cast=bool)

# Stripe (Phase 13)
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")