"""One-time migration of legacy .env API keys into the local settings store.

Provider credentials live in `backend/data/app.db` only — encrypted, managed
through the Settings UI, with exactly one provider active. Nothing on the
request path reads OPENAI_API_KEY & co. any more.

This module exists purely so an existing .env-only install does not break on
upgrade: on the first start after the change, any key still present in the
environment is copied into the database and a flag is written so it never runs
again. After that first start, `backend/.env` can be deleted — and re-adding a
key there will NOT quietly reactivate a provider.
"""

import os

from app.config import LEGACY_ENV_KEYS
from app.store import settings_store

IMPORT_FLAG = "legacy_env_keys_imported"


def _env_key(provider: str) -> str:
    for name in LEGACY_ENV_KEYS.get(provider, ()):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def import_legacy_env_keys() -> list[str]:
    """Copy .env keys into the database once. Returns the providers imported."""
    if settings_store.get_state(IMPORT_FLAG) == "done":
        return []

    imported: list[str] = []
    for provider in LEGACY_ENV_KEYS:
        key = _env_key(provider)
        # A key already saved through the UI always wins over the environment
        stored = settings_store.get_provider(provider) or {}
        if not key or stored.get("api_key"):
            continue
        settings_store.save_provider(provider, api_key=key)
        imported.append(provider)

    # Keep "one active provider" true: if whatever is marked active has no key
    # but something we just imported does, activate that instead.
    if imported:
        active = settings_store.get_active_provider()
        active_settings = settings_store.get_provider(active) or {}
        if not active_settings.get("api_key"):
            settings_store.set_active_provider(imported[0])

    settings_store.set_state(IMPORT_FLAG, "done")
    return imported
