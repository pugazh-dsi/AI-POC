from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.services.document_processor import extract_text, chunk_text
from app.services.embedding_service import get_embeddings
from app.store.vector_store import add_vectors, get_document_list, remove_document

router = APIRouter()


def safe_filename(filename: str) -> str:
    """Reduce a client-supplied filename to a bare name inside UPLOAD_DIR.

    Without this, a filename like "../app/main.py" escapes the uploads
    directory and overwrites arbitrary files.
    """
    name = Path(filename or "").name.replace("\x00", "").strip()
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    resolved = (UPLOAD_DIR / name).resolve()
    if resolved.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename.")

    return name


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = safe_filename(file.filename)

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    file_path = UPLOAD_DIR / filename

    try:
        file_path.write_bytes(content)

        text = await run_in_threadpool(extract_text, file_path)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

        chunks = await run_in_threadpool(chunk_text, text)
        embeddings = await run_in_threadpool(get_embeddings, chunks)

        # Re-uploading a file replaces its vectors instead of indexing it twice
        remove_document(filename)
        num_chunks = add_vectors(embeddings, chunks, filename)

        return {
            "filename": filename,
            "chunks": num_chunks,
            "status": "indexed",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/documents")
async def list_documents():
    return get_document_list()


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    filename = safe_filename(filename)

    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()

    removed = remove_document(filename)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {"filename": filename, "status": "deleted"}
