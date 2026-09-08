"""
AI SDK v4 data-stream formatting, shared by every chat pipeline.

Part codes are validated by @ai-sdk/ui-utils on the client — a malformed part
aborts the stream mid-answer — so every part is built here rather than being
hand-formatted at each call site.

    "0:<json string>"  text chunk
    "8:<json array>"   message annotations (sources, provider, usage)
    "9:<json object>"  tool call    {toolCallId, toolName, args}
    "a:<json object>"  tool result  {toolCallId, result}
    "d:<json object>"  finish message, requires a "finishReason" string
    "3:<json string>"  error

The "9:"/"a:" pair is what `useChat` turns into `message.toolInvocations`, so
tool calls render natively without any custom parsing on the frontend.
"""

import json
from typing import AsyncIterator, Dict


def text_part(content: str) -> str:
    return f"0:{json.dumps(content)}\n"


def annotation_part(data: Dict) -> str:
    return f"8:{json.dumps([data])}\n"


def tool_call_part(tool_call_id: str, tool_name: str, args: Dict) -> str:
    return "9:" + json.dumps({
        "toolCallId": tool_call_id,
        "toolName": tool_name,
        "args": args,
    }) + "\n"


def tool_result_part(tool_call_id: str, result) -> str:
    return "a:" + json.dumps({"toolCallId": tool_call_id, "result": result}) + "\n"


def error_part(message: str) -> str:
    return f"3:{json.dumps(message)}\n"


def finish_part(usage: Dict | None = None) -> str:
    """Without this frame the client streams forever — the UI hangs even though
    the text already arrived."""
    usage = usage or {}
    return "d:" + json.dumps({
        "finishReason": "stop",
        "usage": {
            "promptTokens": usage.get("prompt_tokens", 0),
            "completionTokens": usage.get("completion_tokens", 0),
        },
    }) + "\n"


async def format_sse_stream(generator) -> AsyncIterator[str]:
    """Convert pipeline events into AI SDK v4 parts.

    Accepted event shapes (a pipeline only emits what it needs):
        {"type": "text",        "content": str}
        {"type": "data",        "data": dict}
        {"type": "tool_call",   "id": str, "name": str, "args": dict}
        {"type": "tool_result", "id": str, "result": Any}
    """
    usage = None
    try:
        async for event in generator:
            kind = event["type"]
            if kind == "text":
                yield text_part(event["content"])
            elif kind == "data":
                usage = event["data"].get("usage")
                yield annotation_part(event["data"])
            elif kind == "tool_call":
                yield tool_call_part(event["id"], event["name"], event["args"])
            elif kind == "tool_result":
                yield tool_result_part(event["id"], event["result"])
    except Exception as e:
        print(f"SSE formatting error: {e}")
        yield error_part("An error occurred during streaming.")
        return

    yield finish_part(usage)
