import json
import numpy as np
import faiss

from app.config import FAISS_INDEX_DIR, SIMILARITY_THRESHOLD

INDEX_PATH = FAISS_INDEX_DIR / "index.faiss"
METADATA_PATH = FAISS_INDEX_DIR / "metadata.json"

_index: faiss.IndexFlatL2 | None = None
_metadata: list[dict] = []


def _get_index(dimension: int = 1536) -> faiss.IndexFlatL2:
    global _index
    if _index is None:
        if INDEX_PATH.exists():
            _index = faiss.read_index(str(INDEX_PATH))
        else:
            _index = faiss.IndexFlatL2(dimension)
    return _index


def _load_metadata() -> list[dict]:
    global _metadata
    if not _metadata and METADATA_PATH.exists():
        _metadata = json.loads(METADATA_PATH.read_text())
    return _metadata


def add_vectors(
    embeddings: list[list[float]],
    chunks: list[str],
    filename: str,
) -> int:
    index = _get_index(len(embeddings[0]))
    metadata = _load_metadata()

    vectors = np.array(embeddings, dtype=np.float32)
    index.add(vectors)

    for chunk in chunks:
        metadata.append({"text": chunk, "filename": filename})

    _save()
    return len(chunks)


def search(query_embedding: list[float], top_k: int = 4) -> list[dict]:
    index = _get_index()
    metadata = _load_metadata()

    if index.ntotal == 0:
        return []

    query_vector = np.array([query_embedding], dtype=np.float32)
    distances, indices = index.search(query_vector, min(top_k, index.ntotal))

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(metadata) and idx >= 0:
            distance = float(distances[0][i])
            if distance > SIMILARITY_THRESHOLD:
                continue
            results.append({
                "text": metadata[idx]["text"],
                "filename": metadata[idx]["filename"],
                "score": distance,
            })
    return results


def get_all_chunks(filename: str) -> list[dict]:
    metadata = _load_metadata()
    return [
        {"text": m["text"], "filename": m["filename"], "score": 0.0}
        for m in metadata
        if m["filename"] == filename
    ]


def get_document_list() -> list[dict]:
    metadata = _load_metadata()
    doc_counts: dict[str, int] = {}
    for entry in metadata:
        name = entry["filename"]
        doc_counts[name] = doc_counts.get(name, 0) + 1
    return [{"filename": name, "chunks": count} for name, count in doc_counts.items()]


def remove_document(filename: str) -> bool:
    global _index, _metadata
    _get_index()
    _load_metadata()

    if not any(m["filename"] == filename for m in _metadata):
        return False

    keep_indices = [i for i, m in enumerate(_metadata) if m["filename"] != filename]

    if keep_indices and _index is not None and _index.ntotal > 0:
        all_vectors = np.array([_index.reconstruct(i) for i in keep_indices], dtype=np.float32)
        new_index = faiss.IndexFlatL2(_index.d)
        new_index.add(all_vectors)
        _index = new_index
    else:
        dim = _index.d if _index is not None and _index.d > 0 else 1536
        _index = faiss.IndexFlatL2(dim)

    _metadata = [m for m in _metadata if m["filename"] != filename]
    _save()
    return True


def _save():
    if _index is not None:
        faiss.write_index(_index, str(INDEX_PATH))
    METADATA_PATH.write_text(json.dumps(_metadata))
