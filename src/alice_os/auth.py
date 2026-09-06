from __future__ import annotations

import base64
import hashlib
import json
import secrets
from pathlib import Path

ITERATIONS = 310_000
SESSION_TOKEN_BYTES = 32


def _derive(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return base64.urlsafe_b64encode(digest).decode()


def create_auth_file(path: Path, username: str, password: str) -> None:
    if not username.strip() or len(password) < 12:
        raise ValueError("Username is required and password must be at least 12 characters")
    salt = secrets.token_bytes(16)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "username": username.strip(),
            "salt": base64.urlsafe_b64encode(salt).decode(),
            "password_hash": _derive(password, salt),
            "iterations": ITERATIONS,
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_auth_file(path: Path, username: str, password: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        salt = base64.urlsafe_b64decode(data["salt"])
        expected = str(data["password_hash"])
        actual = _derive(password, salt)
        return secrets.compare_digest(username.strip(), str(data["username"])) and secrets.compare_digest(actual, expected)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def load_or_create_session_token(path: Path) -> str:
    """Return the stable host token used by already-authenticated browsers."""
    try:
        token = path.read_text(encoding="ascii").strip()
        if len(token) >= 40:
            return token
    except OSError:
        pass

    token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(token + "\n", encoding="ascii")
    temporary.replace(path)
    return token
