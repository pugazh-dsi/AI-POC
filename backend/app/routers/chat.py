"""
Streaming chat endpoint compatible with Vercel AI SDK.
Preserves all security features: sanitization, injection detection, rate limiting.
"""

import json
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.sanitizer import sanitize_question, detect_injection
from app.services.qa_service_streaming import answer_question_stream


router = APIRouter()


class Message(BaseModel):
    """AI SDK message format"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """AI SDK chat request format"""
    messages: List[Message]


async def format_sse_stream(generator):
    """
    Convert generator events to AI SDK-compatible Server-Sent Events format.

    AI SDK SSE format:
    - "0:..." for text chunks (streamed content)
    - "2:..." for data events (metadata like sources)
    - Each line is JSON-encoded and newline-terminated
    """
    try:
        async for event in generator:
            if event["type"] == "text":
                # Text chunk: prefix with "0:" (AI SDK text event)
                yield f"0:{json.dumps(event['content'])}\n"
            elif event["type"] == "data":
                # Data event: prefix with "d:" for AI SDK v4 (changed from "2:" in v3)
                # Send as JSON object directly (not wrapped in array)
                yield f"d:{json.dumps(event['data'])}\n"
    except Exception as e:
        # On error, send error event and close stream
        error_msg = "An error occurred during streaming."
        yield f"0:{json.dumps(error_msg)}\n"
        print(f"SSE formatting error: {e}")


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
            yield f"0:{json.dumps(safe_msg)}\n"

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
