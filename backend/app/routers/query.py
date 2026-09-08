from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from app.services.qa_service import answer_question
from app.sanitizer import sanitize_question, detect_injection

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/query")
async def query_documents(request: QueryRequest):
    question = sanitize_question(request.question)

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if detect_injection(question):
        return {
            "answer": "I can only answer questions about your uploaded documents. Please ask a document-related question.",
            "sources": [],
        }

    try:
        result = answer_question(question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")
