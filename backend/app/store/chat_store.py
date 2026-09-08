"""
Local SQLite store for chat history.

Lives in the same backend/data/app.db file as provider settings — one local
file, no external database server. Every turn on every tile is written here,
so a conversation can be re-opened and continued after a reload or a restart.

Shape mirrors what the AI SDK's useChat expects on the client: a session (one
chat) holds an ordered list of messages, each of which may carry annotations
(sources / provider / usage) and tool invocations.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import DATABASE_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         TEXT PRIMARY KEY,
    mode       TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id               TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    role             TEXT NOT NULL,
    content          TEXT NOT NULL DEFAULT '',
    annotations      TEXT NOT NULL DEFAULT '',
    tool_invocations TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages (session_id, created_at);
"""

# The first user message names the chat; anything longer is cut here so the
# sidebar never has to render an essay.
TITLE_MAX = 60

DEFAULT_TITLE = "New chat"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(raw: str, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return fallback


def make_title(text: str) -> str:
    """Derive a sidebar label from the first user message."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return DEFAULT_TITLE
    if len(cleaned) <= TITLE_MAX:
        return cleaned
    return cleaned[: TITLE_MAX - 1].rstrip() + "…"


# -- sessions ---------------------------------------------------------


def create_session(mode: str, title: str = DEFAULT_TITLE) -> Dict[str, Any]:
    session_id = uuid.uuid4().hex
    now = _now()
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO chat_sessions (id, mode, title, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, mode, title or DEFAULT_TITLE, now, now),
        )
    return {
        "id": session_id,
        "mode": mode,
        "title": title or DEFAULT_TITLE,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
        "preview": "",
    }


def get_session(session_id: str) -> Dict[str, Any] | None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None


def list_sessions(mode: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Most recently used first, with a count and a one-line preview so the
    sidebar needs a single request."""
    sql = """
        SELECT s.*,
               (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id)
                   AS message_count,
               (SELECT m.content FROM chat_messages m
                 WHERE m.session_id = s.id AND m.role = 'assistant'
                 ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1)
                   AS preview
          FROM chat_sessions s
    """
    params: list = []
    if mode:
        sql += " WHERE s.mode = ?"
        params.append(mode)
    sql += " ORDER BY s.updated_at DESC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        conn.executescript(SCHEMA)
        rows = conn.execute(sql, params).fetchall()

    sessions = []
    for row in rows:
        record = dict(row)
        preview = " ".join((record.get("preview") or "").split())
        record["preview"] = preview[:120]
        sessions.append(record)
    return sessions


def rename_session(session_id: str, title: str) -> bool:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        changed = conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (make_title(title), _now(), session_id),
        ).rowcount
    return changed > 0


def delete_session(session_id: str) -> bool:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        changed = conn.execute(
            "DELETE FROM chat_sessions WHERE id = ?", (session_id,)
        ).rowcount
    return changed > 0


def delete_sessions(mode: str | None = None) -> int:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        if mode:
            conn.execute(
                "DELETE FROM chat_messages WHERE session_id IN"
                " (SELECT id FROM chat_sessions WHERE mode = ?)",
                (mode,),
            )
            return conn.execute(
                "DELETE FROM chat_sessions WHERE mode = ?", (mode,)
            ).rowcount
        conn.execute("DELETE FROM chat_messages")
        return conn.execute("DELETE FROM chat_sessions").rowcount


# -- messages ---------------------------------------------------------


def add_message(
    session_id: str,
    role: str,
    content: str,
    annotations: List[Dict] | None = None,
    tool_invocations: List[Dict] | None = None,
) -> Dict[str, Any] | None:
    """Append one message and bump the session's updated_at.

    Returns None when the session no longer exists - a chat deleted while its
    answer was still streaming must not resurrect itself.
    """
    now = _now()
    message_id = uuid.uuid4().hex

    with _connect() as conn:
        conn.executescript(SCHEMA)
        session = conn.execute(
            "SELECT id, title FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            return None

        conn.execute(
            """
            INSERT INTO chat_messages
                (id, session_id, role, content, annotations, tool_invocations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                session_id,
                role,
                content,
                json.dumps(annotations) if annotations else "",
                json.dumps(tool_invocations) if tool_invocations else "",
                now,
            ),
        )

        # The first real question names the chat.
        if role == "user" and session["title"] == DEFAULT_TITLE:
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (make_title(content), now, session_id),
            )
        else:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    return {"id": message_id, "role": role, "content": content, "created_at": now}


def get_messages(session_id: str) -> List[Dict[str, Any]]:
    """Messages in the shape the AI SDK's useChat consumes on the client."""
    with _connect() as conn:
        conn.executescript(SCHEMA)
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ?"
            " ORDER BY created_at ASC, rowid ASC",
            (session_id,),
        ).fetchall()

    messages = []
    for row in rows:
        record = dict(row)
        messages.append({
            "id": record["id"],
            "role": record["role"],
            "content": record["content"],
            "createdAt": record["created_at"],
            "annotations": _loads(record["annotations"], None),
            "toolInvocations": _loads(record["tool_invocations"], None),
        })
    return messages
