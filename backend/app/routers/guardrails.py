"""
Guardrails endpoints — extraction (LLM) and validation (deterministic).

    GET  /api/guardrails/rules     the rule pack the engine enforces (UI list)
    GET  /api/guardrails/sample    the reference extraction for LR-2026-001
    POST /api/guardrails/validate  run the rule pack over an extracted payload

The separation the PoC exists to show is visible in the request: `extracted`
is the model's only contribution, and everything the response calls a verdict
was computed in Python from that payload alone.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import UPLOAD_DIR
from app.services.guardrails import describe_pack, evaluate
from app.services.guardrails.extraction import (
    MOCK_LAB_REQUISITION,
    MOCK_SOURCE,
    describe_schema,
    extract_from_file,
    normalize_extraction,
    to_jsonable,
)
from app.services.guardrails.engine import DEFAULT_PACK
from app.services.providers.base import ProviderError
from pydantic import BaseModel

router = APIRouter()


class ValidateRequest(BaseModel):
    # Exactly one source of the payload, in this order of precedence:
    extracted: Optional[Dict[str, Any]] = None  # already-extracted JSON
    filename: Optional[str] = None              # an uploaded document to extract first
    text: Optional[str] = None                  # raw requisition text to extract first
    # Nothing supplied → the reference payload for LR-2026-001, so the engine
    # can be demonstrated without spending a provider call.
    pack: str = DEFAULT_PACK


@router.get("/guardrails/rules")
async def guardrail_rules(pack: str = DEFAULT_PACK):
    """The active rule pack, for the "Active Compliance Guardrails" panel."""
    try:
        return {**describe_pack(pack), "schema": describe_schema()}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/guardrails/sample")
async def guardrail_sample():
    """The reference extraction for the LR-2026-001 requisition."""
    return {
        "source": MOCK_SOURCE,
        "extraction_source": "mock",
        "extracted": to_jsonable(normalize_extraction(MOCK_LAB_REQUISITION)),
    }


@router.post("/guardrails/validate")
async def validate_requisition(request: ValidateRequest):
    """Evaluate an extracted requisition against the rule pack.

    The LLM runs only when the caller passes a document (`filename`/`text`) —
    and only to fill the schema. The verdict itself is always deterministic.
    """
    source = MOCK_SOURCE
    extraction_source = "mock"
    extracted: Dict[str, Any] = MOCK_LAB_REQUISITION
    provider: Dict[str, Any] | None = None
    usage: Dict[str, Any] | None = None

    if request.extracted is not None:
        extracted, source, extraction_source = request.extracted, "client-supplied payload", "client"

    elif request.filename or request.text:
        try:
            if request.filename:
                path = UPLOAD_DIR / request.filename
                # The upload directory only — a filename is user input.
                if path.parent.resolve() != UPLOAD_DIR.resolve() or not path.is_file():
                    raise HTTPException(status_code=404, detail=f"No uploaded file named {request.filename}")
                result = await run_in_threadpool(extract_from_file, path)
                source = request.filename
            else:
                from app.services.guardrails.extraction import extract_lab_requisition

                result = await run_in_threadpool(extract_lab_requisition, request.text)
                source = "pasted text"
        except ProviderError as e:
            raise HTTPException(status_code=503, detail=f"Extraction provider is not ready: {e}")
        except (ValueError, HTTPException) as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=422, detail=f"Extraction failed: {e}")

        extracted = result["payload"]
        provider, usage = result.get("provider"), result.get("usage")
        extraction_source = "llm"

    try:
        verdict = evaluate(extracted, request.pack, source=source)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "source": source,
        "extraction_source": extraction_source,
        "provider": provider,
        "usage": usage,
        "verdict": verdict,
    }
