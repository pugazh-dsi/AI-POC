from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.services.document_processor import extract_text, chunk_text
from app.services.embedding_service import get_embeddings
from app.store.vector_store import add_vectors, get_document_list, remove_document

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    file_path = UPLOAD_DIR / file.filename
    file_path.write_bytes(content)

    try:
        text = extract_text(file_path)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

        chunks = chunk_text(text)
        embeddings = get_embeddings(chunks)
        num_chunks = add_vectors(embeddings, chunks, file.filename)

        return {
            "filename": file.filename,
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
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()

    removed = remove_document(filename)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {"filename": filename, "status": "deleted"}
