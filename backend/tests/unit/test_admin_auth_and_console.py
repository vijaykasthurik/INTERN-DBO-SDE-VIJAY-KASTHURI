"""Unit tests for administrative authentication, rate limiting, permissions, and SQL safety."""

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import _admin_failed_attempts
from app.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.models import AdminAuditLog, Base, User
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def test_db_session():
    """In-memory SQLite session with full schema initialized."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def admin_client(test_db_session: Session):
    """FastAPI TestClient with overridden get_db dependency."""
    test_app = create_app()

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db
    client = TestClient(test_app)
    yield client
    test_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_admin_lockouts():
    """Ensure IP lockout tracker is cleared before and after each test."""
    _admin_failed_attempts.clear()
    yield
    _admin_failed_attempts.clear()


@pytest.fixture
def test_admin_user(test_db_session: Session) -> User:
    """Create a verified administrator account in test database."""
    admin = User(
        email="admin_unit@lumen.internal",
        hashed_password=hash_password("SuperSecretPass2026!#"),
        role="admin",
        is_active=True,
        token_version=1,
    )
    test_db_session.add(admin)
    test_db_session.commit()
    test_db_session.refresh(admin)
    return admin


@pytest.fixture
def regular_user(test_db_session: Session) -> User:
    """Create a standard unprivileged user account in test database."""
    user = User(
        email="regular_unit@lumen.internal",
        hashed_password=hash_password("RegularPassword123!"),
        role="user",
        is_active=True,
        token_version=1,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


def test_admin_login_success(admin_client: TestClient, test_admin_user: User):
    """Admin authenticates with valid credentials and receives an admin-scoped token."""
    resp = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["admin"]["email"] == test_admin_user.email
    assert data["admin"]["role"] == "admin"


def test_admin_login_failure_and_lockout(admin_client: TestClient, test_admin_user: User):
    """5 consecutive failed attempts trigger rate-limit lockout."""
    # 4 failed attempts return 401
    for _ in range(4):
        resp = admin_client.post(
            "/api/v1/admin/login",
            json={"email": test_admin_user.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    # 5th failed attempt returns 401 and trips lockout threshold
    resp5 = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "WrongPassword!"},
    )
    assert resp5.status_code == 401

    # 6th attempt returns 429 Locked Out even with correct password
    resp6 = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    assert resp6.status_code == 429
    assert resp6.json()["code"] == "ADMIN_LOCKED_OUT"


def test_regular_user_access_forbidden(admin_client: TestClient, regular_user: User):
    """Regular user token receives 403 Forbidden on administrative endpoints."""
    token = create_access_token({"sub": str(regular_user.id), "email": regular_user.email})

    headers = {"Authorization": f"Bearer {token}"}
    resp = admin_client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"


def test_totp_enforcement(admin_client: TestClient, test_admin_user: User, monkeypatch):
    """When ADMIN_TOTP_SECRET is configured, TOTP validation is strictly enforced."""
    totp_secret = pyotp.random_base32()
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_totp_secret", totp_secret)

    # Missing TOTP code fails
    resp = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    assert resp.status_code == 401

    # Wrong TOTP code fails
    resp = admin_client.post(
        "/api/v1/admin/login",
        json={
            "email": test_admin_user.email,
            "password": "SuperSecretPass2026!#",
            "totp_code": "000000",
        },
    )
    assert resp.status_code == 401

    # Correct TOTP code succeeds
    valid_totp = pyotp.TOTP(totp_secret).now()
    resp = admin_client.post(
        "/api/v1/admin/login",
        json={
            "email": test_admin_user.email,
            "password": "SuperSecretPass2026!#",
            "totp_code": valid_totp,
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_sql_console_safety_and_execution(admin_client: TestClient, test_admin_user: User):
    """Single-statement SELECT queries succeed; all mutating/DDL statements are rejected."""
    login_resp = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid SELECT
    resp = admin_client.post(
        "/api/v1/admin/database/query",
        json={"query": "SELECT id, email, role FROM users LIMIT 5"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert "rows" in data
    assert data["row_count"] >= 1

    # 2. DROP TABLE rejected
    resp_drop = admin_client.post(
        "/api/v1/admin/database/query",
        json={"query": "DROP TABLE users"},
        headers=headers,
    )
    assert resp_drop.status_code == 400
    assert resp_drop.json()["code"] == "SECURITY_VIOLATION"

    # 3. DELETE rejected
    resp_delete = admin_client.post(
        "/api/v1/admin/database/query",
        json={"query": "DELETE FROM users WHERE id = 1"},
        headers=headers,
    )
    assert resp_delete.status_code == 400
    assert resp_delete.json()["code"] == "SECURITY_VIOLATION"

    # 4. Multi-statement injection rejected
    resp_multi = admin_client.post(
        "/api/v1/admin/database/query",
        json={"query": "SELECT 1; DROP TABLE users;"},
        headers=headers,
    )
    assert resp_multi.status_code == 400
    assert resp_multi.json()["code"] == "SECURITY_VIOLATION"


def test_user_disable_and_token_invalidation(admin_client: TestClient, test_admin_user: User, regular_user: User):
    """Disabling a user revokes their session immediately."""
    user_token = create_access_token(
        {"sub": str(regular_user.id), "email": regular_user.email, "ver": regular_user.token_version}
    )

    admin_login = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Disable regular user
    resp = admin_client.patch(
        f"/api/v1/admin/users/{regular_user.id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Attempt request with old user token -> rejected (401)
    user_headers = {"Authorization": f"Bearer {user_token}"}
    probe = admin_client.get("/api/v1/auth/me", headers=user_headers)
    assert probe.status_code == 401


def test_database_table_browser_and_secret_reveal(
    admin_client: TestClient, test_admin_user: User, test_db_session: Session
):
    """Verify secrets are masked as '***' and reveal endpoint logs an audit record."""
    admin_login = admin_client.post(
        "/api/v1/admin/login",
        json={"email": test_admin_user.email, "password": "SuperSecretPass2026!#"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Browse users table
    browse_resp = admin_client.get("/api/v1/admin/database/browse/users", headers=headers)
    assert browse_resp.status_code == 200
    rows = browse_resp.json()["rows"]
    assert len(rows) > 0
    # hashed_password must be masked
    for r in rows:
        assert r["hashed_password"] == "***"

    # Reveal secret
    reveal_resp = admin_client.post(
        f"/api/v1/admin/database/reveal-secret?table_name=users&row_id={test_admin_user.id}&column_name=hashed_password",
        headers=headers,
    )
    assert reveal_resp.status_code == 200
    unmasked = reveal_resp.json()["value"]
    assert unmasked.startswith("$argon2")

    # Verify audit log entry
    audit = (
        test_db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "secret.revealed")
        .first()
    )
    assert audit is not None
    assert audit.target_type == "users"
    assert audit.target_id == str(test_admin_user.id)
