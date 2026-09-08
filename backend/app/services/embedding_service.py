"""
OpenAI embeddings.

Embeddings are deliberately NOT provider-switchable: the FAISS index stores
1536-dimension ada-002 vectors and SIMILARITY_THRESHOLD=1.8 is tuned to that
model's L2 distances. The key is resolved lazily so a key saved through the
settings UI takes effect without restarting the server.
"""

from openai import OpenAI, OpenAIError

from app.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE
from app.services.providers import get_embedding_api_key
from app.services.providers.base import ProviderError

_cache: dict = {"api_key": None, "client": None}


def _get_client() -> OpenAI:
    api_key = get_embedding_api_key()
    if not api_key:
        raise ProviderError(
            "An OpenAI API key is required for document embeddings. "
            "Add one under Settings — it is needed even when chat runs on another provider."
        )

    if _cache["api_key"] != api_key:
        _cache["api_key"] = api_key
        _cache["client"] = OpenAI(api_key=api_key)

    return _cache["client"]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed texts, batching so large documents don't exceed OpenAI's per-request
    input limit (a 10MB upload produces >12,000 chunks)."""
    client = _get_client()
    embeddings: list[list[float]] = []

    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        except OpenAIError as e:
            raise ProviderError(f"Embedding request failed: {e}") from e

        # Sort by index — the API does not guarantee response ordering
        embeddings.extend(
            item.embedding for item in sorted(response.data, key=lambda d: d.index)
        )

    return embeddings


def get_embedding(text: str) -> list[float]:
    return get_embeddings([text])[0]
