"""
The rule engine: YAML pack in, verdict out.

It owns no policy of its own. It loads a pack, hands each rule's args to the
operator named in rules/ops.py, and aggregates the three possible statuses into
one document-level verdict:

    every rule passed                     -> compliant
    any rule failed                       -> non_compliant
    otherwise, any rule not evaluable     -> incomplete   (held, not released)

`not_evaluable` is deliberately not a pass. A field the LLM could not read is a
reason to stop, which is what "fail closed" means here.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.services.guardrails.extraction import normalize_extraction, to_jsonable
from app.services.guardrails.rules import ops

PACKS_DIR = Path(__file__).parent / "rules" / "packs"
DEFAULT_PACK = "lab_requisition"

# Document-level outcomes.
COMPLIANT = "compliant"
NON_COMPLIANT = "non_compliant"
INCOMPLETE = "incomplete"

_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}


def load_pack(name: str = DEFAULT_PACK) -> Dict[str, Any]:
    """Read a rule pack, re-reading it when the file changes on disk."""
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"Invalid rule pack name: {name}")

    path = PACKS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No rule pack named '{name}' in {PACKS_DIR}")

    mtime = path.stat().st_mtime
    cached = _CACHE.get(name)
    if cached and cached[0] == mtime:
        return cached[1]

    pack = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(pack.get("rules"), list) or not pack["rules"]:
        raise ValueError(f"Rule pack '{name}' declares no rules")

    _CACHE[name] = (mtime, pack)
    return pack


def describe_pack(name: str = DEFAULT_PACK) -> Dict[str, Any]:
    """The pack as the UI shows it — the client-facing guardrail list."""
    pack = load_pack(name)
    return {
        "pack": pack.get("pack", name),
        "version": pack.get("version"),
        "title": pack.get("title", name),
        "description": (pack.get("description") or "").strip(),
        "document_type": pack.get("document_type"),
        "guardrails": [
            {
                "id": rule["id"],
                "name": rule.get("name", rule["id"]),
                "severity": rule.get("severity", "medium"),
                "category": rule.get("category"),
                "title": (rule.get("display", {}).get("title") or rule.get("name", rule["id"])).strip(),
                "description": (rule.get("display", {}).get("description") or "").strip(),
                "rationale": (rule.get("rationale") or "").strip(),
                "operator": rule.get("op"),
                "fields": rule.get("fields", []),
            }
            for rule in pack["rules"]
        ],
    }


def _evaluate_rule(rule: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run one rule's operator, turning any operator error into not_evaluable.

    A broken rule must never look like a pass, and must never take the whole
    validation down with it.
    """
    display = rule.get("display", {}) or {}
    base = {
        "id": rule.get("id"),
        "name": rule.get("name", rule.get("id")),
        "title": (display.get("title") or rule.get("name") or rule.get("id", "")).strip(),
        "description": (display.get("description") or "").strip(),
        "severity": rule.get("severity", "medium"),
        "category": rule.get("category"),
        "operator": rule.get("op"),
        "fields": rule.get("fields", []),
    }

    try:
        operator = ops.get_op(rule.get("op", ""))
        outcome = operator(payload, **(rule.get("args") or {}))
    except Exception as e:  # a malformed pack or an operator bug
        outcome = {
            "status": ops.NOT_EVALUABLE,
            "message": f"Rule could not be executed: {e}",
            "details": {"error": type(e).__name__},
        }

    result = {
        **base,
        "status": outcome.get("status", ops.NOT_EVALUABLE),
        "message": outcome.get("message", ""),
        "details": outcome.get("details", {}),
    }
    if result["status"] != ops.PASS:
        result["remediation"] = (rule.get("remediation") or "").strip()
    return result


def evaluate(
    extracted: Dict[str, Any],
    pack_name: str = DEFAULT_PACK,
    source: str | None = None,
) -> Dict[str, Any]:
    """Evaluate an extracted payload against a rule pack.

    `extracted` may be raw (JSON strings from the model) or already normalized;
    it is normalized either way so the operators always see real dates and bools.
    """
    pack = load_pack(pack_name)
    payload = normalize_extraction(extracted)

    results = [_evaluate_rule(rule, payload) for rule in pack["rules"]]

    passed = [r for r in results if r["status"] == ops.PASS]
    failed = [r for r in results if r["status"] == ops.FAIL]
    not_evaluable = [r for r in results if r["status"] == ops.NOT_EVALUABLE]

    if failed:
        status = NON_COMPLIANT
    elif not_evaluable:
        status = INCOMPLETE
    else:
        status = COMPLIANT

    blocking = set(pack.get("blocking_severities") or [])
    blocked = bool(not_evaluable) or any(r["severity"] in blocking for r in failed)

    return {
        "pack": pack.get("pack", pack_name),
        "pack_version": pack.get("version"),
        "document_type": pack.get("document_type"),
        "source": source,
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "blocked": blocked,
        "headline": _headline(status, failed, not_evaluable),
        "summary": {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "not_evaluable": len(not_evaluable),
        },
        "extracted": to_jsonable(payload),
        "missing_fields": sorted(
            {field for field, value in payload.items() if value is None or value == []}
        ),
        "results": results,
    }


def _headline(status: str, failed: List[Dict], not_evaluable: List[Dict]) -> str:
    if status == NON_COMPLIANT:
        ids = ", ".join(r["id"] for r in failed)
        return f"{len(failed)} guardrail(s) failed ({ids}). The requisition is held for correction."
    if status == INCOMPLETE:
        ids = ", ".join(r["id"] for r in not_evaluable)
        return (
            f"{len(not_evaluable)} guardrail(s) could not be evaluated ({ids}) because fields are "
            "missing. Failing closed — the requisition is held."
        )
    return "All guardrails passed. The requisition can be released to the LIS."
