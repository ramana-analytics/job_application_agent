"""
Simple user authentication — register, login, session tokens.
Passwords hashed with PBKDF2-SHA256 (stdlib only, no extra deps).
Sessions stored in data/sessions.json with 30-day TTL.
"""
import hashlib
import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
SESSION_TTL_HOURS = 720  # 30 days


def _read(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000
    ).hex()


def register_user(username: str, password: str, email: str = "") -> dict:
    """Register a new user. Raises ValueError on validation errors."""
    username = username.strip()
    key = username.lower()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    users = _read(USERS_FILE)
    if key in users:
        raise ValueError("Username already taken")
    salt = os.urandom(32).hex()
    users[key] = {
        "username": username,
        "email": email.strip(),
        "password_hash": _hash(password, salt),
        "salt": salt,
        "created_at": datetime.utcnow().isoformat(),
    }
    _write(USERS_FILE, users)
    return {"username": username, "email": email.strip()}


def login_user(username: str, password: str) -> Optional[str]:
    """Validate credentials; return session token on success, None on failure."""
    users = _read(USERS_FILE)
    user = users.get(username.strip().lower())
    if not user:
        return None
    if _hash(password, user["salt"]) != user["password_hash"]:
        return None
    token = str(uuid.uuid4())
    sessions = _read(SESSIONS_FILE)
    sessions[token] = {
        "username": user["username"],
        "expires_at": (
            datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
        ).isoformat(),
    }
    _write(SESSIONS_FILE, sessions)
    return token


def validate_token(token: str) -> Optional[dict]:
    """Return {'username': ...} if token is valid, else None."""
    if not token:
        return None
    sessions = _read(SESSIONS_FILE)
    s = sessions.get(token)
    if not s:
        return None
    if datetime.utcnow() > datetime.fromisoformat(s["expires_at"]):
        sessions.pop(token)
        _write(SESSIONS_FILE, sessions)
        return None
    return {"username": s["username"]}


def logout_user(token: str):
    """Invalidate a session token."""
    sessions = _read(SESSIONS_FILE)
    if token in sessions:
        sessions.pop(token)
        _write(SESSIONS_FILE, sessions)
