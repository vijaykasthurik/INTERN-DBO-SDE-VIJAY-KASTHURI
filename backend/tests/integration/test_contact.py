from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.contact import _attempts
from app.db.models import Base, ContactMessage
from app.db.session import get_db
from app.main import create_app


def test_contact_validation_storage_honeypot_and_limit():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    _attempts.clear()
    with TestClient(app) as client:
        body = {"name": "Analyst", "email": "analyst@example.com", "message": "Please help with an upload."}
        assert client.post("/api/v1/contact", json={**body, "email": "bad"}).status_code == 422
        assert client.post("/api/v1/contact", json=body).status_code == 201
        assert db.query(ContactMessage).count() == 1
        assert client.post("/api/v1/contact", json={**body, "website": "spam"}).status_code == 201
        assert db.query(ContactMessage).count() == 1
        for _ in range(3):
            assert client.post("/api/v1/contact", json=body).status_code == 201
        assert client.post("/api/v1/contact", json=body).status_code == 429
    _attempts.clear()
    db.close()
    engine.dispose()
