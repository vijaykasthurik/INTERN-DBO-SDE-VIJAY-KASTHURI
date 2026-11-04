"""Authentication API router: register, login, refresh, me endpoints."""

import contextlib
import os
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.data.ingestion import DataIngestionPipeline
from app.db.models import ChatSession, Dataset, MetricDefinition, User
from app.db.session import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    """User login payload."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str


class AuthTokenResponse(BaseModel):
    """JWT Token response pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseModel):
    """Current authenticated user profile."""

    id: int
    email: str
    is_active: bool
    created_at: datetime


@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)) -> UserProfileResponse:
    """Register a new user account with argon2 password hashing."""
    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise ValidationError(f"Account with email {req.email} already exists")

    hashed = hash_password(req.password)
    user = User(
        email=req.email.lower().strip(),
        hashed_password=hashed,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    """Authenticate credentials and generate token pair."""
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is inactive")

    sub = str(user.id)
    access_token = create_access_token({"sub": sub, "email": user.email})
    refresh_token = create_refresh_token({"sub": sub, "email": user.email})

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_tokens(req: RefreshRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    """Exchange valid refresh token for a new token pair."""
    try:
        claims = decode_token(req.refresh_token)
    except Exception as exc:
        raise AuthenticationError(f"Invalid refresh token: {exc}") from exc

    if claims.get("type") != "refresh":
        raise AuthenticationError("Provided token is not a refresh token")

    user_id = claims.get("sub")
    if not user_id:
        raise AuthenticationError("Token payload missing subject identifier")

    user = db.query(User).filter(User.id == int(str(user_id)), User.is_active.is_(True)).first()
    if not user:
        raise AuthenticationError("User not found or inactive")

    sub = str(user.id)
    new_access = create_access_token({"sub": sub, "email": user.email})
    new_refresh = create_refresh_token({"sub": sub, "email": user.email})

    return AuthTokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return identity of the authenticated caller."""
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/clear-data", status_code=status.HTTP_200_OK)
async def clear_user_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Wipe all datasets, metrics, and chat sessions for the current user and reset their DuckDB."""
    db.query(Dataset).filter(Dataset.user_id == user.id).delete()
    db.query(ChatSession).filter(ChatSession.user_id == user.id).delete()
    db.query(MetricDefinition).filter(MetricDefinition.user_id == user.id).delete()
    db.commit()

    pipeline = DataIngestionPipeline()
    db_path = pipeline.get_user_db_path(user.id)
    if os.path.exists(db_path):
        with contextlib.suppress(Exception):
            os.remove(db_path)

    return {"message": "All user data, datasets, and chat sessions have been permanently cleared."}

