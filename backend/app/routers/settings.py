"""
Provider settings API.

API keys are stored encrypted in the local SQLite database and are NEVER
returned to the client — only a masked hint (sk-...b3f9).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.crypto import mask
from app.services.providers import (
    PROVIDER_CATALOG,
    build_provider,
    get_active_provider_id,
    resolve_settings,
)
from app.services.providers.base import ProviderError
from app.store import settings_store

router = APIRouter()


class ProviderUpdate(BaseModel):
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_version: str | None = None


def _require_known(provider: str) -> None:
    if provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")


def _describe(provider: str, active: str) -> dict:
    catalog = PROVIDER_CATALOG[provider]
    settings = resolve_settings(provider)

    return {
        "id": provider,
        "label": catalog["label"],
        "notes": catalog["notes"],
        "fields": catalog["fields"],
        "models": catalog["models"],
        "model": settings["model"],
        "base_url": settings["base_url"],
        "api_version": settings["api_version"],
        "masked_key": mask(settings["api_key"]),
        "configured": bool(settings["api_key"]),
        "key_from_env": settings["api_key_from_env"],
        "is_active": provider == active,
    }


@router.get("/providers")
async def list_providers():
    active = get_active_provider_id()
    return {
        "active": active,
        "providers": [_describe(p, active) for p in PROVIDER_CATALOG],
    }


@router.put("/providers/{provider}")
async def update_provider(provider: str, update: ProviderUpdate):
    _require_known(provider)

    fields = update.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No settings provided.")

    settings_store.save_provider(provider, **fields)
    return _describe(provider, get_active_provider_id())


@router.post("/providers/{provider}/activate")
async def activate_provider(provider: str):
    _require_known(provider)

    settings = resolve_settings(provider)
    if not settings["api_key"]:
        raise HTTPException(
            status_code=400,
            detail=f"Add an API key for {PROVIDER_CATALOG[provider]['label']} before activating it.",
        )

    settings_store.set_active_provider(provider)
    return {"active": provider, "providers": [_describe(p, provider) for p in PROVIDER_CATALOG]}


@router.post("/providers/{provider}/test")
async def test_provider(provider: str):
    """Validate stored credentials with a minimal live call."""
    _require_known(provider)

    try:
        instance = await run_in_threadpool(build_provider, provider)
        await run_in_threadpool(instance.check)
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")

    return {"provider": provider, "model": instance.model, "status": "ok"}


@router.delete("/providers/{provider}")
async def delete_provider(provider: str):
    _require_known(provider)

    if not settings_store.delete_provider(provider):
        raise HTTPException(status_code=404, detail="Provider is not configured.")

    return {"provider": provider, "status": "deleted"}
