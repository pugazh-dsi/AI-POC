"""
Guardrails for healthcare lab requisitions.

The split this package exists to enforce:

    LLM   → extraction only. Unstructured document text in, strict JSON out
            (extraction.py). It never decides whether a requisition is compliant.
    Python → the decision. A declarative YAML rule pack (rules/packs/) evaluated
            by deterministic operators (rules/ops.py) through engine.py.

So a compliance verdict is reproducible: the same extracted payload always
yields the same verdict, and every rule that fired can be pointed at a line of
YAML rather than at a model's opinion.
"""

from app.services.guardrails.engine import evaluate, load_pack, describe_pack
from app.services.guardrails.extraction import (
    LAB_REQ_SCHEMA,
    MOCK_LAB_REQUISITION,
    describe_schema,
    extract_lab_requisition,
    normalize_extraction,
)

__all__ = [
    "LAB_REQ_SCHEMA",
    "MOCK_LAB_REQUISITION",
    "describe_pack",
    "describe_schema",
    "evaluate",
    "extract_lab_requisition",
    "load_pack",
    "normalize_extraction",
]
