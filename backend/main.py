"""
Flight Assistant AI — FastAPI entry point.
Phase 14: Production REST API with authentication and all services exposed.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import APP_NAME, APP_VERSION, ALLOWED_ORIGINS, DISABLE_TRACING, DEFAULT_PROVIDER
from config.model_config import DEFAULT_MODEL
from database.database import init_db

from agents import set_tracing_disabled

# API routes
from api import auth, flights, bookings, payments, assistant
from api.payment_webhook import router as webhook_router

logger = logging.getLogger(__name__)

if DISABLE_TRACING:
    set_tracing_disabled(True)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "AI Flight Booking & Travel Assistant — production REST API exposing "
        "flight search, bookings, payments, and an OpenAI Agents SDK-powered "
        "intelligent assistant with session persistence."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "system", "description": "Health check and diagnostics"},
        {"name": "authentication", "description": "User registration, login, and profile"},
        {"name": "flights", "description": "Flight search, details, filtering, pricing, and seat availability"},
        {"name": "bookings", "description": "Create, retrieve, confirm, and cancel flight bookings (authenticated, ownership-enforced)"},
        {"name": "payments", "description": "Optional Stripe payment module (future). Returns 503 when Stripe is not configured; booking confirmation does not require payment."},
        {"name": "assistant", "description": "AI flight assistant chat with conversation persistence and guardrails"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return controlled JSON for HTTP errors — never leaks internals."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all safety net: log the real error, return a safe generic 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


# Health check
@app.get("/api/health", tags=["system"])
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "ai_provider": DEFAULT_PROVIDER,
        "model": DEFAULT_MODEL.model if hasattr(DEFAULT_MODEL, "model") else str(DEFAULT_MODEL),
    }


# Root status
@app.get("/", tags=["system"])
async def root():
    """Welcome endpoint with developer-facing service navigation."""
    return {
        "name": APP_NAME,
        "description": "AI-powered flight booking and travel assistant",
        "version": APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
    }


# Include API routers
app.include_router(auth.router)
app.include_router(flights.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(assistant.router)
app.include_router(webhook_router)
