"""RAG exposed as two tools, so the model chooses retrieval instead of always
being handed context.

Retrieval itself is unchanged — same embedding model, same FAISS search, same
SIMILARITY_THRESHOLD filter as the RAG tile. Only the trigger differs.
"""

from app.config import TOP_K_RESULTS
from app.services.embedding_service import get_embedding
from app.services.providers.base import ProviderError
from app.store.vector_store import get_document_list, search

# Passages are trimmed before going back to the model: several full 1000-char
# chunks as a tool result would crowd out the rest of the conversation.
SNIPPET_CHARS = 600
MAX_RESULTS = 10


def list_documents() -> dict:
    """List the uploaded documents and their chunk counts."""
    documents = get_document_list()
    return {
        "count": len(documents),
        "documents": documents,
    }


def search_documents(query: str, top_k: int = TOP_K_RESULTS) -> dict:
    """Semantic search over the uploaded documents."""
    query = (query or "").strip()
    if not query:
        return {"error": "No search query provided."}

    if not get_document_list():
        return {
            "query": query,
            "match_count": 0,
            "matches": [],
            "note": "No documents have been uploaded yet.",
        }

    try:
        top_k = max(1, min(int(top_k or TOP_K_RESULTS), MAX_RESULTS))
    except (TypeError, ValueError):
        top_k = TOP_K_RESULTS

    try:
        embedding = get_embedding(query)
    except ProviderError as e:
        return {"query": query, "error": str(e)}

    # search() already drops anything past SIMILARITY_THRESHOLD
    results = search(embedding, top_k=top_k)

    return {
        "query": query,
        "match_count": len(results),
        "matches": [
            {
                "filename": r["filename"],
                "distance": round(r["score"], 4),
                "text": r["text"][:SNIPPET_CHARS],
            }
            for r in results
        ],
        "note": (
            "No passage in the uploaded documents was close enough to the query."
            if not results
            else "Answer only from these passages and cite the filenames."
        ),
    }


LIST_SCHEMA = {
    "name": "list_documents",
    "description": (
        "List the documents currently uploaded to the knowledge base, with the "
        "number of indexed chunks for each. Use this to see what is available "
        "before searching."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

SEARCH_SCHEMA = {
    "name": "search_documents",
    "description": (
        "Semantic search over the user's uploaded documents. Use this for any "
        "question about document contents. Returns the closest passages with "
        "their source filenames — answer only from those passages."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for. A descriptive phrase works better than a single keyword.",
            },
            "top_k": {
                "type": "integer",
                "description": f"How many passages to return (1-{MAX_RESULTS}). Defaults to {TOP_K_RESULTS}.",
            },
        },
        "required": ["query"],
    },
}
