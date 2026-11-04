"""Unit tests for Lumen health and configuration endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Test client fixture."""
    app = create_app()
    return TestClient(app)


def test_health_check_returns_200(client: TestClient) -> None:
    """Verify /health returns HTTP 200 with ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "environment" in data


def test_health_check_api_prefix(client: TestClient) -> None:
    """Verify /api/v1/health also returns HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_check_returns_200(client: TestClient) -> None:
    """Verify /ready returns ready: true."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["database"] == "connected"
    assert data["storage"] == "writable"


def test_provider_status_endpoint(client: TestClient) -> None:
    """Verify /providers/status exposes primary provider."""
    response = client.get("/api/v1/providers/status")
    assert response.status_code == 200
    data = response.json()
    assert data["primary_provider"] in ("mock", "groq")
    assert "mock" in data["providers"]
    assert data["providers"]["mock"]["available"] is True


def test_settings_singleton_and_defaults() -> None:
    """Verify configuration settings load with sensible defaults."""
    settings = get_settings()
    assert settings.llm_provider in ("mock", "groq")
    assert len(settings.cors_origins_list) > 0
    assert len(settings.fallback_providers_list) > 0
