"""
Local SQLite store for AI provider configuration and API keys.

Lives in backend/data/app.db — a plain file inside the repo, no external
database server. API keys are encrypted before they are written.
"""

import sqlite3
from datetime import datetime, timezone

from app.config import DATABASE_FILE, DEFAULT_CHAT_PROVIDER
from app.crypto import encrypt, decrypt

SCHEMA = """
CREATE TABLE IF NOT EXISTS provider_settings (
    provider          TEXT PRIMARY KEY,
    api_key_encrypted TEXT NOT NULL DEFAULT '',
    model             TEXT NOT NULL DEFAULT '',
    base_url          TEXT NOT NULL DEFAULT '',
    deployment        TEXT NOT NULL DEFAULT '',
    api_version       TEXT NOT NULL DEFAULT '',
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

ACTIVE_PROVIDER_KEY = "active_chat_provider"

_EDITABLE = ("model", "base_url", "deployment", "api_version")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_provider(provider: str, **fields) -> None:
    """Upsert one provider's settings.

    Only keys present in `fields` are written, so updating the model does not
    wipe a stored API key. Passing api_key="" explicitly clears the key.
    """
    api_key = fields.pop("api_key", None)

    with _connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute(
            "SELECT * FROM provider_settings WHERE provider = ?", (provider,)
        ).fetchone()

        current = dict(row) if row else {
            "api_key_encrypted": "",
            **{f: "" for f in _EDITABLE},
        }

        if api_key is not None:
            current["api_key_encrypted"] = encrypt(api_key) if api_key else ""

        for field in _EDITABLE:
            value = fields.get(field)
            if value is not None:
                current[field] = value

        conn.execute(
            """
            INSERT INTO provider_settings
                (provider, api_key_encrypted, model, base_url, deployment, api_version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
                api_key_encrypted = excluded.api_key_encrypted,
                model             = excluded.model,
                base_url          = excluded.base_url,
                deployment        = excluded.deployment,
                api_version       = excluded.api_version,
                updated_at        = excluded.updated_at
            """,
            (
                provider,
                current["api_key_encrypted"],
                current["model"],
                current["base_url"],
                current["deployment"],
                current["api_version"],
                _now(),
            ),
        )


def get_provider(provider: str) -> dict | None:
    """Return one provider's settings with the API key DECRYPTED.

    Internal use only — never return this straight to a client.
    """
    with _connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute(
            "SELECT * FROM provider_settings WHERE provider = ?", (provider,)
        ).fetchone()

    if row is None:
        return None

    record = dict(row)
    record["api_key"] = decrypt(record.pop("api_key_encrypted", ""))
    return record


def all_providers() -> dict[str, dict]:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        rows = conn.execute("SELECT * FROM provider_settings").fetchall()

    result = {}
    for row in rows:
        record = dict(row)
        record["api_key"] = decrypt(record.pop("api_key_encrypted", ""))
        result[record["provider"]] = record
    return result


def delete_provider(provider: str) -> bool:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        changed = conn.execute(
            "DELETE FROM provider_settings WHERE provider = ?", (provider,)
        ).rowcount
    return changed > 0


def get_active_provider() -> str:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = ?", (ACTIVE_PROVIDER_KEY,)
        ).fetchone()
    return row["value"] if row else DEFAULT_CHAT_PROVIDER


def set_active_provider(provider: str) -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            """
            INSERT INTO app_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (ACTIVE_PROVIDER_KEY, provider),
        )
