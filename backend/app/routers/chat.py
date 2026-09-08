"""
Streaming chat endpoint compatible with Vercel AI SDK.
Preserves all security features: sanitization, injection detection, rate limiting.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.sanitizer import sanitize_question, detect_injection
from app.services.chat_history import ensure_session, record_stream, save_message
from app.services.qa_service_streaming import answer_question_stream
from app.sse import format_sse_stream, finish_part, text_part


router = APIRouter()

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Critical for nginx/proxy streaming
}


class Message(BaseModel):
    """AI SDK message format"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """AI SDK chat request format.

    chatId is the stored conversation this turn belongs to. It is optional so
    the endpoint keeps working for any client that doesn't track history; when
    it is missing a fresh conversation is opened and its id comes back on the
    X-Chat-Id response header.
    """
    messages: List[Message]
    chatId: str | None = None


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

    Both the question and the answer are written to the chat store, so the
    conversation can be re-opened and continued later.

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

    # History is recorded around the pipeline, never inside it — a failed write
    # degrades to "this turn isn't saved", it never breaks the answer.
    session_id = await ensure_session(request.chatId, "rag")
    headers = {**STREAM_HEADERS, "X-Chat-Id": session_id or ""}
    await save_message(session_id, "user", user_message)

    # SECURITY LAYER 2: Prompt injection detection (same as non-streaming)
    if detect_injection(question):
        # Block immediately - return safe response without calling OpenAI
        safe_msg = "I can only answer questions about your uploaded documents."

        async def blocked_response():
            yield text_part(safe_msg)
            yield finish_part()

        await save_message(session_id, "assistant", safe_msg)

        return StreamingResponse(
            blocked_response(), media_type="text/event-stream", headers=headers
        )

    # SECURITY PRESERVED: Call streaming QA service (same RAG pipeline + prompt hardening)
    return StreamingResponse(
        format_sse_stream(record_stream(session_id, answer_question_stream(question))),
        media_type="text/event-stream",
        headers=headers,
    )
