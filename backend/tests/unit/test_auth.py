"""Unit and integration tests for Authentication and Argon2/JWT security."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def test_db_session():
    """In-memory SQLite session for isolated unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_client(test_db_session):
    """FastAPI test client with overridden test database dependency."""
    app = create_app()

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_argon2_hashing_and_verification():
    """Verify Argon2id password hashing produces verifiable hashes."""
    pwd = "EnterpriseSecurePassword123!"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2id$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_encode_and_decode():
    """Verify JWT access token creation and claim parsing."""
    claims = {"sub": "42", "email": "analyst@lumen.ai"}
    token = create_access_token(claims)
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["email"] == "analyst@lumen.ai"
    assert decoded["type"] == "access"


def test_auth_registration_and_login_flow(auth_client: TestClient):
    """Verify registration, login, and profile inspection lifecycle."""
    # 1. Register
    reg_resp = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "alice@company.com", "password": "SuperSecretPassword123!"},
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == "alice@company.com"
    assert user_data["is_active"] is True

    # 2. Duplicate registration fails with 422
    dup_resp = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "alice@company.com", "password": "SuperSecretPassword123!"},
    )
    assert dup_resp.status_code == 422

    # 3. Login
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@company.com", "password": "SuperSecretPassword123!"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # 4. Access /me with token
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = auth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@company.com"

    # 5. Refresh token exchange
    ref_resp = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert ref_resp.status_code == 200
    assert "access_token" in ref_resp.json()
