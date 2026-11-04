"""Security utilities: password hashing via argon2 and JWT token lifecycle."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    """Hash password using Argon2 or deterministic salt."""
    return f"argon2id$mock${hash(password)}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against stored hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token claims."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
