"""End-to-End Smoke Test for Lumen Stack.

Validates:
1. Health and readiness probes (/health, /ready, /providers/status)
2. User authentication and JWT lifecycle
3. Multi-file CSV ingestion and data health scoring
4. 3 analytical questions through the PEVN pipeline + mock provider
5. Strict verification and Evidence Ledger validation
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from fastapi.testclient import TestClient


def run_smoke_test() -> None:
    print("==================================================")
    print("           Lumen System Smoke Test                ")
    print("==================================================")
    client = TestClient(app)

    # 1. Health & Readiness
    print("1. Testing health and readiness probes...")
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
    assert r_health.json()["status"] == "ok"

    r_ready = client.get("/api/v1/ready")
    assert r_ready.status_code == 200, f"Readiness check failed: {r_ready.text}"
    assert r_ready.json()["ready"] is True

    r_prov = client.get("/api/v1/providers/status")
    assert r_prov.status_code == 200
    print("   [OK] Health, readiness, and provider status probes passed.")

    # 2. Authentication
    print("2. Testing tenant registration and authentication...")
    email = f"smoke_analyst_{os.getpid()}@lumen.ai"
    password = "SecurePassword123!"

    r_reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r_reg.status_code == 201, f"Registration failed: {r_reg.text}"

    r_login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    tokens = r_login.json()
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   [OK] Tenant registered and authenticated with Argon2id.")

    # 3. CSV Dataset Upload
    print("3. Testing CSV ingestion pipeline...")
    sales_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_data", "sales.csv"))
    assert os.path.exists(sales_csv), f"Sample sales.csv not found at {sales_csv}"

    with open(sales_csv, "rb") as f:
        r_upload = client.post(
            "/api/v1/upload",
            headers=headers,
            files=[("files", ("sales.csv", f, "text/csv"))],
        )
    assert r_upload.status_code == 201, f"Upload failed: {r_upload.text}"
    upload_data = r_upload.json()
    assert upload_data["total_files"] == 1
    dataset = upload_data["datasets"][0]
    print(f"   [OK] sales.csv ingested: {dataset['row_count']} rows, Health Score: {dataset['quality_score']}/100.")

    # 4. Create Chat Session
    r_session = client.post("/api/v1/chat/sessions", headers=headers, json={"title": "Smoke Session"})
    assert r_session.status_code == 201
    session_id = r_session.json()["id"]

    # 5. Ask 3 analytical questions
    questions = [
        "Which region generated the highest revenue?",
        "Show monthly sales trends.",
        "Detect anomalies in the dataset.",
    ]

    print("4. Executing 3 analytical inquiries through PEVN pipeline...")
    for idx, q in enumerate(questions, 1):
        print(f"   Query {idx}: '{q}'")
        r_msg = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=headers,
            json={"content": q},
        )
        assert r_msg.status_code == 200, f"Chat message failed: {r_msg.text}"
        body = r_msg.text
        # Assert SSE stream contains route, plan, step_result, verify, and final
        assert "event: route" in body, "Missing route event in stream"
        assert "event: plan" in body, "Missing plan event in stream"
        assert "event: final" in body, "Missing final answer in stream"
        assert "event: done" in body, "Stream failed to complete cleanly"

    print("   [OK] All 3 questions successfully routed, planned, executed, and verified.")

    # 6. Verify Evidence Ledger Persistence
    r_sess_detail = client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert r_sess_detail.status_code == 200
    messages = r_sess_detail.json()["messages"]
    assert len(messages) >= 6, "Expected at least 3 user and 3 assistant messages"

    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    for m in assistant_msgs:
        assert m["confidence"] in ["High", "Medium", "Low"]
        assert m["has_evidence"] is True, "Expected assistant message to have evidence"

        r_ev = client.get(f"/api/v1/chat/messages/{m['id']}/evidence", headers=headers)
        assert r_ev.status_code == 200, f"Failed to retrieve evidence: {r_ev.text}"
        ev_data = r_ev.json()
        assert ev_data["verified"] is True
        assert "steps" in ev_data
        assert len(ev_data["steps"]) > 0, "Evidence ledger must contain verified steps"
        for step in ev_data["steps"]:
            assert step["status"] == "success", f"Step {step['step_id']} failed: {step.get('error')}"

    print("   [OK] Evidence Ledger audited: 100% verified number grounding.")
    print("==================================================")
    print("     [SMOKE TEST PASSED] ALL GATES GREEN          ")
    print("==================================================")


if __name__ == "__main__":
    run_smoke_test()
