"""
Encryption for API keys held in the local database.

Keys are encrypted at rest so a copied app.db does not hand over live
credentials. The master key comes from APP_SECRET_KEY when set, otherwise it is
generated once and stored next to the database with owner-only permissions.
"""

import os
import stat

from cryptography.fernet import Fernet, InvalidToken

from app.config import APP_SECRET_KEY, SECRET_KEY_FILE

_fernet: Fernet | None = None


def _load_key() -> bytes:
    if APP_SECRET_KEY:
        return APP_SECRET_KEY.encode()

    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    SECRET_KEY_FILE.write_bytes(key)
    os.chmod(SECRET_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_key())
    return _fernet


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Return the plaintext key, or "" if it can't be decrypted (rotated master key)."""
    if not token:
        return ""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""


def mask(api_key: str) -> str:
    """Render a key for display without exposing it: sk-...b3f9"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:3]}...{api_key[-4:]}"
