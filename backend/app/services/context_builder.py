"""
Shared context assembly for the QA services.

Retrieval (especially the summary path, which pulls *every* chunk of a document)
can easily produce more text than the model's context window holds. Building the
context through a token budget keeps large documents answerable instead of
failing the request outright.
"""

import tiktoken

from app.config import LLM_MODEL, MAX_CONTEXT_TOKENS

try:
    _ENCODING = tiktoken.encoding_for_model(LLM_MODEL)
except Exception:
    _ENCODING = tiktoken.get_encoding("cl100k_base")

SEPARATOR = "\n\n---\n\n"


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def build_context(results: list[dict], max_tokens: int = MAX_CONTEXT_TOKENS) -> tuple[str, list[dict]]:
    """Join retrieved chunks into a context string that fits the token budget.

    Returns the context and the chunks that actually made it in, so callers
    report sources for the passages the model really saw.
    """
    parts: list[str] = []
    used: list[dict] = []
    total = 0

    for r in results:
        piece = f"[From: {r['filename']}]\n{r['text']}"
        cost = count_tokens(piece) + (count_tokens(SEPARATOR) if parts else 0)
        if total + cost > max_tokens:
            break
        parts.append(piece)
        used.append(r)
        total += cost

    return SEPARATOR.join(parts), used
