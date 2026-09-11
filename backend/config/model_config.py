"""
Centralized model configuration layer.
Supports Gemini and Groq via the OpenAI-compatible interface used by the Agents SDK.
Switch providers by setting DEFAULT_PROVIDER in .env.
"""
from agents import AsyncOpenAI, OpenAIChatCompletionsModel
from .settings import (
    DEFAULT_PROVIDER,
    GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL_NAME,
    GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL_NAME,
)


def _build_gemini_model() -> OpenAIChatCompletionsModel:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in .env")
    client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    return OpenAIChatCompletionsModel(model=GEMINI_MODEL_NAME, openai_client=client)


def _build_groq_model() -> OpenAIChatCompletionsModel:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in .env")
    client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    return OpenAIChatCompletionsModel(model=GROQ_MODEL_NAME, openai_client=client)


def get_model(provider: str | None = None) -> OpenAIChatCompletionsModel:
    """Return the AI model for the given provider (or the default)."""
    chosen = (provider or DEFAULT_PROVIDER).lower()
    if chosen == "gemini":
        return _build_gemini_model()
    if chosen == "groq":
        return _build_groq_model()
    raise ValueError(f"Unknown provider '{chosen}'. Supported: gemini, groq")


# Pre-built default — imported by agents so they don't call get_model() repeatedly.
DEFAULT_MODEL = get_model()
