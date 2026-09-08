"""
Tool Calling endpoints.

The security pipeline is identical to /api/chat — sanitize, then injection
check before any provider call. Tools widen what the model can reach, so the
defenses matter more here, not less.
"""

from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.sanitizer import sanitize_question, detect_injection
from app.services.tool_service import answer_with_tools
from app.services.tools import describe_tools
from app.sse import format_sse_stream, finish_part, text_part

router = APIRouter()

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Critical for nginx/proxy streaming
}


class Message(BaseModel):
    role: str
    content: str


class ToolChatRequest(BaseModel):
    messages: List[Message]


@router.get("/tools")
async def list_tools():
    """The tool catalog the model is given, for the UI to display."""
    tools = describe_tools()
    return {"count": len(tools), "tools": tools}


@router.post("/tools/chat")
async def tools_chat_stream(request: ToolChatRequest):
    """Streaming endpoint for the Tool Calling tile (AI SDK useChat)."""
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found in request")

    # SECURITY LAYER 1: Input sanitization
    question = sanitize_question(user_message)

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty after sanitization")

    # SECURITY LAYER 2: Prompt injection detection — blocks before the model,
    # and therefore before any tool, is reached.
    if detect_injection(question):
        async def blocked_response():
            yield text_part(
                "That request was blocked before reaching the model. "
                "I can answer questions using the available tools."
            )
            yield finish_part()

        return StreamingResponse(
            blocked_response(), media_type="text/event-stream", headers=STREAM_HEADERS
        )

    # Prior turns give the model conversational context; the last user message
    # is passed separately because it is the sanitized one.
    history = [
        {"role": m.role, "content": m.content} for m in request.messages[:-1]
    ]

    return StreamingResponse(
        format_sse_stream(answer_with_tools(question, history)),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
