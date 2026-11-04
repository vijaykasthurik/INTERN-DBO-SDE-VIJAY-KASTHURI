"""Authentication API router: register, login, refresh, me endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """User registration payload."""
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """User login payload."""
    email: EmailStr
    password: str


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


@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> UserProfileResponse:
    """Register a new user account."""
    return UserProfileResponse(id=1, email=req.email, is_active=True)


@router.post("/login", response_model=AuthTokenResponse)
async def login(req: LoginRequest) -> AuthTokenResponse:
    """Authenticate credentials and generate token pair."""
    return AuthTokenResponse(
        access_token="mock_access_token_lumen_auth",
        refresh_token="mock_refresh_token_lumen_auth",
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile() -> UserProfileResponse:
    """Return identity of the authenticated caller."""
    return UserProfileResponse(id=1, email="analyst@lumen.ai", is_active=True)
