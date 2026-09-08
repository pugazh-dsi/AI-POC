"""
Chat history: list, read, rename and delete stored conversations.

Every tile writes its turns through app.services.chat_history; this router is
the read/manage side the sidebar uses. Sessions are scoped by `mode` ('rag',
'tools', ...) so each tile lists only its own conversations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store import chat_store

router = APIRouter()


class NewChat(BaseModel):
    mode: str = Field(default="rag", max_length=32)
    title: str | None = Field(default=None, max_length=200)


class RenameChat(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.get("/chats")
async def list_chats(mode: str | None = None, limit: int = 100):
    """Recent conversations, newest activity first."""
    limit = max(1, min(limit, 500))
    chats = chat_store.list_sessions(mode=mode, limit=limit)
    return {"count": len(chats), "chats": chats}


@router.post("/chats")
async def create_chat(payload: NewChat):
    """Start a new conversation. The first question renames it automatically."""
    title = chat_store.make_title(payload.title) if payload.title else chat_store.DEFAULT_TITLE
    return chat_store.create_session(payload.mode, title)


@router.get("/chats/{chat_id}")
async def read_chat(chat_id: str):
    """One conversation with its full transcript, ready for useChat."""
    chat = chat_store.get_session(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"chat": chat, "messages": chat_store.get_messages(chat_id)}


@router.patch("/chats/{chat_id}")
async def rename_chat(chat_id: str, payload: RenameChat):
    if not chat_store.rename_session(chat_id, payload.title):
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_store.get_session(chat_id)


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    if not chat_store.delete_session(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted", "id": chat_id}
