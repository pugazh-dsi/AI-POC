"""
AI provider registry.

Resolves the active chat provider from the local database — `backend/data/app.db`
— and nowhere else. Keys are never read from the environment at request time, so
the only way to configure a provider is the Settings UI, and exactly one provider
is active at a time. (A legacy .env key is copied into the database once by
app/store/bootstrap.py; see that module.)

Embeddings stay on OpenAI: the FAISS index is built from 1536-dimension
ada-002 vectors and SIMILARITY_THRESHOLD=1.8 is calibrated to that model's
distances, so a different embedding model would invalidate the whole index.
"""

from app.config import DEFAULT_CHAT_PROVIDER, LLM_MODEL
from app.store import settings_store
from app.services.providers.base import ChatProvider, ProviderError
from app.services.providers.anthropic_provider import AnthropicChatProvider
from app.services.providers.gemini_provider import GeminiChatProvider
from app.services.providers.openai_provider import (
    AzureOpenAIChatProvider,
    OpenAIChatProvider,
)

# Describes each provider for the settings UI: which fields it needs, which
# models to suggest, and which brand mark to draw. `model` is always free text
# so a newer model can be used without a code change. `icon` is a slug the
# frontend maps to an SVG (components/ProviderIcon.jsx) — keep the two in sync.
PROVIDER_CATALOG: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "icon": "openai",
        "default_model": LLM_MODEL,
        "models": ["gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "fields": ["api_key", "model"],
        "notes": "Also supplies the embeddings for document search.",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "icon": "anthropic",
        "default_model": "claude-opus-5",
        "models": [
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-opus-4-8",
            "claude-haiku-4-5",
        ],
        "fields": ["api_key", "model"],
        "notes": "Chat only — Anthropic has no embeddings API.",
    },
    "gemini": {
        "label": "Google Gemini",
        "icon": "gemini",
        "default_model": "gemini-2.5-flash",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "fields": ["api_key", "model"],
        "notes": "Chat only in this app.",
    },
    "azure_openai": {
        "label": "Azure OpenAI",
        "icon": "azure",
        "default_model": "",
        "models": [],
        "fields": ["api_key", "model", "base_url", "api_version"],
        "notes": "Model is your deployment name. Endpoint looks like https://<resource>.openai.azure.com.",
    },
}

def resolve_settings(provider: str) -> dict:
    """Merge the provider's stored settings with the catalog defaults."""
    if provider not in PROVIDER_CATALOG:
        raise ProviderError(f"Unknown provider: {provider}")

    catalog = PROVIDER_CATALOG[provider]
    stored = settings_store.get_provider(provider) or {}

    return {
        "provider": provider,
        "api_key": stored.get("api_key", ""),
        "model": stored.get("model") or catalog["default_model"],
        "base_url": stored.get("base_url", ""),
        "api_version": stored.get("api_version", ""),
    }


def build_provider(provider: str) -> ChatProvider:
    """Instantiate a configured chat provider."""
    settings = resolve_settings(provider)
    model = settings["model"]
    api_key = settings["api_key"]

    if not model:
        raise ProviderError(
            f"No model configured for {PROVIDER_CATALOG[provider]['label']}."
        )

    if provider == "openai":
        return OpenAIChatProvider(model, api_key)
    if provider == "anthropic":
        return AnthropicChatProvider(model, api_key)
    if provider == "gemini":
        return GeminiChatProvider(model, api_key)
    if provider == "azure_openai":
        return AzureOpenAIChatProvider(
            model, api_key, settings["base_url"], settings["api_version"]
        )

    raise ProviderError(f"Unknown provider: {provider}")


def get_active_provider_id() -> str:
    active = settings_store.get_active_provider()
    return active if active in PROVIDER_CATALOG else DEFAULT_CHAT_PROVIDER


def get_active_chat_provider() -> ChatProvider:
    return build_provider(get_active_provider_id())


def get_embedding_api_key() -> str:
    """Embeddings always run on OpenAI — see the module docstring."""
    return resolve_settings("openai")["api_key"]


def is_configured(provider: str) -> bool:
    return bool(resolve_settings(provider)["api_key"])
