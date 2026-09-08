"""
Persistence tap for the streaming pipelines.

Every tile streams pipeline events (text / data / tool_call / tool_result) into
app.sse.format_sse_stream. `record_stream` sits between the two: it passes each
event straight through untouched and, when the stream ends, writes the finished
assistant message to chat_store so the turn can be re-read later.

It must never change what the client sees - a history feature that can break an
answer is worse than no history - so the persistence write is wrapped and its
failures are logged, not raised. The write happens in `finally` so a client that
disconnects mid-answer still keeps the part that was generated.
"""

from typing import Any, AsyncGenerator, Dict, List

from starlette.concurrency import run_in_threadpool

from app.store import chat_store


async def ensure_session(session_id: str | None, mode: str) -> str | None:
    """Return a usable session id, creating one if the client didn't send it.

    Returns None if history could not be written at all, in which case the
    caller simply streams without persisting.
    """
    try:
        if session_id:
            existing = await run_in_threadpool(chat_store.get_session, session_id)
            if existing:
                return session_id
        session = await run_in_threadpool(chat_store.create_session, mode)
        return session["id"]
    except Exception as e:  # noqa: BLE001
        print(f"Chat history unavailable (session): {e}")
        return None


async def save_message(
    session_id: str | None,
    role: str,
    content: str,
    annotations: List[Dict] | None = None,
    tool_invocations: List[Dict] | None = None,
) -> None:
    if not session_id:
        return
    try:
        await run_in_threadpool(
            chat_store.add_message, session_id, role, content, annotations,
            tool_invocations,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Chat history write failed ({role}): {e}")


async def record_stream(
    session_id: str | None, generator: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[Dict[str, Any], None]:
    """Pass pipeline events through, then store the assembled answer."""
    if not session_id:
        async for event in generator:
            yield event
        return

    text: List[str] = []
    annotations: List[Dict] = []
    # Keyed by tool call id so the "a:" result lands on the "9:" call it
    # belongs to, exactly as useChat pairs them on the client.
    invocations: Dict[str, Dict[str, Any]] = {}

    try:
        async for event in generator:
            kind = event.get("type")
            if kind == "text":
                text.append(event.get("content", ""))
            elif kind == "data":
                annotations.append(event["data"])
            elif kind == "tool_call":
                invocations[event["id"]] = {
                    "toolCallId": event["id"],
                    "toolName": event["name"],
                    "args": event.get("args") or {},
                    "state": "call",
                }
            elif kind == "tool_result":
                invocation = invocations.setdefault(
                    event["id"],
                    {"toolCallId": event["id"], "toolName": "", "args": {}},
                )
                invocation["state"] = "result"
                invocation["result"] = event.get("result")
            yield event
    finally:
        content = "".join(text)
        if content or invocations:
            await save_message(
                session_id,
                "assistant",
                content,
                annotations or None,
                list(invocations.values()) or None,
            )
