"""Dependency injection providers for FastAPI routes."""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db


def get_current_settings() -> Settings:
    """Provide application settings dependency."""
    return get_settings()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Extract, decode JWT bearer token, and return authenticated User entity."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1]
    try:
        claims = decode_token(token)
    except Exception as exc:
        raise AuthenticationError(f"Invalid or expired authentication token: {exc}") from exc

    if claims.get("type") != "access":
        raise AuthenticationError("Provided token is not an access token")

    user_id = claims.get("sub")
    if not user_id:
        raise AuthenticationError("Token payload missing subject identifier")

    user = db.query(User).filter(User.id == int(str(user_id)), User.is_active.is_(True)).first()
    if not user:
        raise AuthenticationError("User not found or inactive")

    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Extract authenticated User entity if present, otherwise return None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            return None
        user_id = claims.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(str(user_id)), User.is_active.is_(True)).first()
    except Exception:
        return None
