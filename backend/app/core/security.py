"""Security utilities: password hashing via Argon2, TOTP, and JWT token lifecycle."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using Argon2id with secure defaults."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against stored Argon2 hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def verify_totp(code: str, secret: str) -> bool:
    """Validate time-based one-time password (RFC 6238)."""
    if not secret or not secret.strip():
        return True
    try:
        import pyotp

        totp = pyotp.TOTP(secret.strip())
        return bool(totp.verify(code.strip()))
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_admin_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate short-lived signed JWT access token for administrative operations."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.admin_jwt_expire_minutes))
    to_encode.update({"exp": expire, "type": "access", "aud": "admin", "role": "admin"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate signed JWT refresh token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(days=settings.jwt_refresh_expire_days))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, audience: str | None = None) -> dict[str, Any]:
    """Decode and validate JWT token claims."""
    settings = get_settings()
    options: dict[str, Any] = {"verify_aud": audience is not None}
    kwargs: dict[str, Any] = {"options": options}
    if audience:
        kwargs["audience"] = audience
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm], **kwargs)
