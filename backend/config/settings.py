from decouple import config

# Application
APP_NAME = config("APP_NAME", default="Flight Assistant AI")
APP_VERSION = config("APP_VERSION", default="1.0.0")
DEBUG = config("DEBUG", default=False, cast=bool)

# CORS
ALLOWED_ORIGINS = config("ALLOWED_ORIGINS", default="http://localhost:3000").split(",")

# Database
DATABASE_URL = config("DATABASE_URL", default="sqlite:///./flight_assistant.db")

# AI Provider
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

# JWT Authentication (Phase 14)
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = config("JWT_EXPIRATION_HOURS", default=24, cast=int)
