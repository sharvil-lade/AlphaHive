"""Password hashing and session-token signing.

Passwords are SHA-256 pre-hashed before bcrypt sees them, to sidestep bcrypt's silent
72-byte truncation. Sessions are signed JWTs in an httpOnly cookie — there is no
session table, so rotating `SECRET_KEY` revokes every session.
"""

import base64
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

logger = logging.getLogger("security")

_ALGORITHM = "HS256"


def _prehash(password: str) -> bytes:
    """SHA-256 -> base64 so every password is a fixed 44 bytes, under bcrypt's 72-byte cap."""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the DB — a failed login, never a 500.
        return False


def encode_session(session_id: str, user_id: str | None = None, email: str | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(days=settings.SESSION_TTL_DAYS),
    }
    if user_id:
        payload["uid"] = user_id
        payload["email"] = email
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_session(token: str) -> dict[str, Any] | None:
    """Return the token payload, or None if it is expired, forged, or malformed."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
