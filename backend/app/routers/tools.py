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
from app.services.chat_history import ensure_session, record_stream, save_message
from app.services.tool_service import answer_with_tools
from app.services.tools import describe_integrations, describe_tools, set_tool_enabled
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


class ToolToggleRequest(BaseModel):
    enabled: bool


class ToolChatRequest(BaseModel):
    messages: List[Message]
    # The stored conversation this turn belongs to; a new one is opened when
    # the client doesn't send it (its id comes back on X-Chat-Id).
    chatId: str | None = None


@router.get("/tools")
async def list_tools():
    """The tool catalog the model is given, for the UI to display.

    Every tool is listed, including switched-off ones (`enabled: False`) so the
    UI can offer them back — only `get_tool_schemas()` filters those out before
    the model sees them. `integrations` is the grouping the tile renders.
    """
    tools = describe_tools()
    return {
        "count": len(tools),
        "enabled_count": len([t for t in tools if t["enabled"]]),
        "integrations": describe_integrations(),
        "tools": tools,
    }


@router.patch("/tools/{name}")
async def toggle_tool(name: str, request: ToolToggleRequest):
    """Switch one tool on or off.

    Disabling genuinely removes the capability: the tool is dropped from the
    schemas handed to the model and `run_tool()` refuses it, so this is not a
    display-only filter.
    """
    if not set_tool_enabled(name, request.enabled):
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

    tools = describe_tools()
    updated = next(t for t in tools if t["name"] == name)

    return {
        "tool": updated,
        "enabled_count": len([t for t in tools if t["enabled"]]),
        "integrations": describe_integrations(),
    }


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

    # History is recorded around the pipeline, never inside it — a failed write
    # degrades to "this turn isn't saved", it never breaks the answer.
    session_id = await ensure_session(request.chatId, "tools")
    headers = {**STREAM_HEADERS, "X-Chat-Id": session_id or ""}
    await save_message(session_id, "user", user_message)

    # SECURITY LAYER 2: Prompt injection detection — blocks before the model,
    # and therefore before any tool, is reached.
    if detect_injection(question):
        blocked_msg = (
            "That request was blocked before reaching the model. "
            "I can answer questions using the available tools."
        )

        async def blocked_response():
            yield text_part(blocked_msg)
            yield finish_part()

        await save_message(session_id, "assistant", blocked_msg)

        return StreamingResponse(
            blocked_response(), media_type="text/event-stream", headers=headers
        )

    # Prior turns give the model conversational context; the last user message
    # is passed separately because it is the sanitized one.
    history = [
        {"role": m.role, "content": m.content} for m in request.messages[:-1]
    ]

    return StreamingResponse(
        format_sse_stream(record_stream(session_id, answer_with_tools(question, history))),
        media_type="text/event-stream",
        headers=headers,
    )
