"""Tenant isolation tests proving strict multi-tenant boundary enforcement."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
def client(test_db_session):
    app = create_app()

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_user_tenant_data_isolation(client: TestClient):
    """Prove that User A cannot view, modify, or delete datasets belonging to User B."""
    # 1. Register User A and User B
    client.post("/api/v1/auth/register", json={"email": "userA@lumen.ai", "password": "Password123!"})
    login_a = client.post("/api/v1/auth/login", json={"email": "userA@lumen.ai", "password": "Password123!"}).json()
    token_a = login_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post("/api/v1/auth/register", json={"email": "userB@lumen.ai", "password": "Password123!"})
    login_b = client.post("/api/v1/auth/login", json={"email": "userB@lumen.ai", "password": "Password123!"}).json()
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. User A uploads a private dataset
    csv_content = b"id,val\n1,100\n2,200\n"
    upload_resp = client.post(
        "/api/v1/upload",
        files={"files": ("private_a.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers_a,
    )
    assert upload_resp.status_code == 201
    dataset_a_id = upload_resp.json()["datasets"][0]["id"]

    # 3. User A can see their dataset
    list_a = client.get("/api/v1/datasets", headers=headers_a)
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["id"] == dataset_a_id

    # 4. User B lists datasets: should be empty (cannot see User A's dataset)
    list_b = client.get("/api/v1/datasets", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # 5. User B attempts direct GET of User A's dataset -> 403 Forbidden
    detail_b = client.get(f"/api/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert detail_b.status_code == 403

    # 6. User B attempts DELETE of User A's dataset -> 403 Forbidden
    del_b = client.delete(f"/api/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert del_b.status_code == 403

    # 7. Confirm User A's dataset remains intact
    detail_a = client.get(f"/api/v1/datasets/{dataset_a_id}", headers=headers_a)
    assert detail_a.status_code == 200
    assert detail_a.json()["name"] == "private_a.csv"
