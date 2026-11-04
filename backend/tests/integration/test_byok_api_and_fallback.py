"""Integration tests for BYOK API lifecycle, user isolation, and smart router fallback."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.llm.pool import GroqKeyEntry, GroqKeyPool, check_and_record_shared_quota
from app.llm.validator import ValidationResult
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_byok_api_lifecycle_and_isolation(client: TestClient) -> None:
    # 1. Register User A and User B
    email_a = "user_a_byok@lumen.ai"
    email_b = "user_b_byok@lumen.ai"
    pw = "SecurePassword123!"

    client.post("/api/v1/auth/register", json={"email": email_a, "password": pw})
    res_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pw})
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post("/api/v1/auth/register", json={"email": email_b, "password": pw})
    res_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pw})
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Mock live validation for testing
    mock_val = ValidationResult(
        valid=True,
        status="active",
        message="Key verified",
        models=["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        model_fast="llama-3.1-8b-instant",
        model_strong="llama-3.3-70b-versatile",
    )

    with patch("app.api.byok.validate_user_api_key", new_callable=AsyncMock) as mocked_validate:
        mocked_validate.return_value = mock_val

        # A) Validate without storing
        r_val = client.post(
            "/api/v1/me/ai-connection/validate",
            headers=headers_a,
            json={"provider_id": "groq", "api_key": "gsk_user_a_secret_key_1234"},
        )
        assert r_val.status_code == 200
        assert r_val.json()["valid"] is True

        # B) Store/Replace User A Key
        r_put = client.put(
            "/api/v1/me/ai-connection",
            headers=headers_a,
            json={
                "provider_id": "groq",
                "api_key": "gsk_user_a_secret_key_1234",
                "label": "My Groq Key",
                "allow_shared_fallback": True,
            },
        )
        assert r_put.status_code == 200
        data_a = r_put.json()
        assert data_a["connected"] is True
        assert data_a["provider_id"] == "groq"
        assert data_a["key_hint"] == "...1234"
        # Zero secret exposure check: raw key must never be in response
        assert "gsk_user_a_secret_key_1234" not in str(r_put.text)

    # 3. Isolation Check: User B cannot see User A's connection
    r_get_b = client.get("/api/v1/me/ai-connection", headers=headers_b)
    assert r_get_b.status_code == 200
    assert r_get_b.json()["connected"] is False

    # 4. User A reads their connection
    r_get_a = client.get("/api/v1/me/ai-connection", headers=headers_a)
    assert r_get_a.status_code == 200
    assert r_get_a.json()["connected"] is True
    assert r_get_a.json()["label"] == "My Groq Key"

    # 5. Patch Connection
    r_patch = client.patch(
        "/api/v1/me/ai-connection",
        headers=headers_a,
        json={"label": "Updated Groq Label", "allow_shared_fallback": False},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["label"] == "Updated Groq Label"
    assert r_patch.json()["allow_shared_fallback"] is False

    # 6. Delete Connection
    r_del = client.delete("/api/v1/me/ai-connection", headers=headers_a)
    assert r_del.status_code == 204

    r_get_after = client.get("/api/v1/me/ai-connection", headers=headers_a)
    assert r_get_after.json()["connected"] is False


def test_groq_key_pool_round_robin_and_cooldown() -> None:
    pool = GroqKeyPool()
    pool.entries = [
        GroqKeyEntry(index=1, key="k1"),
        GroqKeyEntry(index=2, key="k2"),
        GroqKeyEntry(index=3, key="k3"),
    ]

    # Acquire round-robin
    k1 = pool.acquire_active_key()
    assert k1 is not None and k1.key == "k1"

    k2 = pool.acquire_active_key()
    assert k2 is not None and k2.key == "k2"

    # Simulate 429 on k2
    pool.record_outcome(k2, "rate_limited")
    assert k2.status == "cooling_down"

    # Next acquire skips k2
    k3 = pool.acquire_active_key()
    assert k3 is not None and k3.key == "k3"

    next_k = pool.acquire_active_key()
    assert next_k is not None and next_k.key == "k1"  # Skips cooling k2


def test_shared_pool_hourly_quota_enforcement() -> None:
    test_uid = 998877
    # Exhaust quota up to limit
    for _ in range(30):
        allowed, rem = check_and_record_shared_quota(test_uid)
        assert allowed is True

    # 31st request is blocked
    allowed, rem = check_and_record_shared_quota(test_uid)
    assert allowed is False
    assert rem == 0
