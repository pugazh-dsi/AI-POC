"""
Local store for the systems the Tool Calling tile connects OUT to.

Two kinds live here, both in the same `backend/data/app.db` as provider
settings and chat history:

    'aws'  one connected AWS account (access key / secret / region)
    'mcp'  any number of MCP servers (url + optional bearer token)

The whole config blob is Fernet-encrypted before it is written, exactly like a
provider API key, because it carries live credentials. Nothing here returns the
plaintext to a client — `public_view()` is what the API is allowed to send.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import DATABASE_FILE
from app.crypto import encrypt, decrypt, mask

SCHEMA = """
CREATE TABLE IF NOT EXISTS connections (
    id         TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    label      TEXT NOT NULL DEFAULT '',
    config     TEXT NOT NULL DEFAULT '',
    enabled    INTEGER NOT NULL DEFAULT 1,
    status     TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""

# The one AWS account: a fixed id, so connecting again updates it rather than
# stacking up accounts the tools would have to choose between.
AWS_ID = "aws"

# Config keys that must never leave the backend in the clear.
SECRET_FIELDS = ("secret_access_key", "session_token", "auth_token")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode(row: sqlite3.Row) -> Dict[str, Any]:
    """Row → dict with `config` decrypted. Internal use only."""
    try:
        config = json.loads(decrypt(row["config"]) or "{}")
    except (ValueError, TypeError):
        # A rotated master key makes the blob unreadable; treat it as empty
        # rather than taking the whole connections list down.
        config = {}

    try:
        status = json.loads(row["status"] or "{}")
    except (ValueError, TypeError):
        status = {}

    return {
        "id": row["id"],
        "kind": row["kind"],
        "label": row["label"],
        "config": config if isinstance(config, dict) else {},
        "enabled": bool(row["enabled"]),
        "status": status if isinstance(status, dict) else {},
        "updated_at": row["updated_at"],
    }


def save_connection(
    conn_id: str,
    kind: str,
    label: str = "",
    config: Dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> Dict[str, Any]:
    """Upsert one connection.

    `config` is merged into what is stored, so updating the region does not
    wipe the secret key. A field passed as "" is cleared deliberately.
    """
    with _connect() as db:
        db.executescript(SCHEMA)
        row = db.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()
        existing = _decode(row) if row else None

        merged = dict(existing["config"]) if existing else {}
        for key, value in (config or {}).items():
            if value is not None:
                merged[key] = value

        record = {
            "label": label or (existing["label"] if existing else ""),
            "enabled": existing["enabled"] if enabled is None and existing else (
                True if enabled is None else enabled
            ),
            "status": existing["status"] if existing else {},
        }

        db.execute(
            """
            INSERT INTO connections (id, kind, label, config, enabled, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind       = excluded.kind,
                label      = excluded.label,
                config     = excluded.config,
                enabled    = excluded.enabled,
                updated_at = excluded.updated_at
            """,
            (
                conn_id,
                kind,
                record["label"],
                encrypt(json.dumps(merged)),
                1 if record["enabled"] else 0,
                json.dumps(record["status"]),
                _now(),
            ),
        )

    return get_connection(conn_id)


def new_connection_id() -> str:
    return uuid.uuid4().hex[:12]


def get_connection(conn_id: str) -> Dict[str, Any] | None:
    """One connection with its secrets DECRYPTED — never return this directly."""
    with _connect() as db:
        db.executescript(SCHEMA)
        row = db.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()
    return _decode(row) if row else None


def list_connections(kind: str | None = None) -> List[Dict[str, Any]]:
    """All connections (secrets decrypted), optionally of one kind."""
    with _connect() as db:
        db.executescript(SCHEMA)
        if kind:
            rows = db.execute(
                "SELECT * FROM connections WHERE kind = ? ORDER BY updated_at", (kind,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM connections ORDER BY kind, updated_at").fetchall()
    return [_decode(row) for row in rows]


def set_status(conn_id: str, status: Dict[str, Any]) -> None:
    """Record the result of the last connection test.

    Kept out of `config` so it is never encrypted/decrypted with the secrets and
    can be read cheaply — it must therefore never contain a credential.
    """
    with _connect() as db:
        db.executescript(SCHEMA)
        db.execute(
            "UPDATE connections SET status = ?, updated_at = ? WHERE id = ?",
            (json.dumps(status), _now(), conn_id),
        )


def set_enabled(conn_id: str, enabled: bool) -> bool:
    with _connect() as db:
        db.executescript(SCHEMA)
        changed = db.execute(
            "UPDATE connections SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, _now(), conn_id),
        ).rowcount
    return changed > 0


def delete_connection(conn_id: str) -> bool:
    with _connect() as db:
        db.executescript(SCHEMA)
        changed = db.execute("DELETE FROM connections WHERE id = ?", (conn_id,)).rowcount
    return changed > 0


def public_view(connection: Dict[str, Any]) -> Dict[str, Any]:
    """The shape the API may return: every secret replaced by a mask.

    A field is masked rather than dropped so the UI can show that a credential
    is stored without ever receiving it.
    """
    config = {}
    for key, value in connection["config"].items():
        if key in SECRET_FIELDS:
            config[key] = mask(str(value)) if value else ""
            config[f"{key}_set"] = bool(value)
        else:
            config[key] = value

    return {
        "id": connection["id"],
        "kind": connection["kind"],
        "label": connection["label"],
        "config": config,
        "enabled": connection["enabled"],
        "status": connection["status"],
        "updated_at": connection["updated_at"],
    }
