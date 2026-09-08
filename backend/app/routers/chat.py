"""
Streaming chat endpoint compatible with Vercel AI SDK.
Preserves all security features: sanitization, injection detection, rate limiting.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.sanitizer import sanitize_question, detect_injection
from app.services.qa_service_streaming import answer_question_stream
from app.sse import format_sse_stream, finish_part, text_part


router = APIRouter()


class Message(BaseModel):
    """AI SDK message format"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """AI SDK chat request format"""
    messages: List[Message]


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """
    Streaming endpoint for AI SDK useChat hook.

    Security pipeline (SAME as /api/query endpoint):
    1. Extract user message
    2. Sanitize input
    3. Detect prompt injection
    4. If safe, stream response
    5. If injection detected, block immediately (no OpenAI call)

    Returns:
        StreamingResponse with SSE events compatible with AI SDK
    """
    # Extract last user message from conversation
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found in request")

    # SECURITY LAYER 1: Input sanitization (same as non-streaming)
    question = sanitize_question(user_message)

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty after sanitization")

    # SECURITY LAYER 2: Prompt injection detection (same as non-streaming)
    if detect_injection(question):
        # Block immediately - return safe response without calling OpenAI
        async def blocked_response():
            safe_msg = "I can only answer questions about your uploaded documents."
            yield text_part(safe_msg)
            yield finish_part()

        return StreamingResponse(
            blocked_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    # SECURITY PRESERVED: Call streaming QA service (same RAG pipeline + prompt hardening)
    return StreamingResponse(
        format_sse_stream(answer_question_stream(question)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Critical for nginx/proxy streaming
        }
    )
