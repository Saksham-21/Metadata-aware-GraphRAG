"""
app/core/security.py
────────────────────
Password hashing, JWT creation/verification, and role constants.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# Using bcrypt directly — passlib 1.7.4 is abandoned and broken with bcrypt 4.x


def hash_password(plain: str) -> str:
    """Return bcrypt hash of a plain-text password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str,        # user UUID as string
    role: str,           # e.g. "admin", "developer", "ba"
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT.

    Payload claims:
        sub   → user UUID (string)
        role  → user role string
        exp   → expiry timestamp
        iat   → issued-at timestamp
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.

    Returns the payload dict on success.
    Raises jose.JWTError on invalid/expired token (caller handles).
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ── Role constants ────────────────────────────────────────────────────────────
class Role:
    ADMIN = "admin"
    DEVELOPER = "developer"
    BA = "ba"
    VIEWER = "viewer"

    # Ordered by privilege level (highest → lowest)
    ALL: list[str] = [ADMIN, DEVELOPER, BA, VIEWER]

    # What each role is allowed to do is enforced in dependencies.py
    # via require_roles() — keep this file pure constants only.
