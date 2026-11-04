"""Integration tests for Phase 4: Agent engine PEVN pipeline, SSE streaming, and Ground Truth benchmarks."""

import contextlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.models import Base, User
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def agent_test_env():
    """Create test database with test user and authenticated TestClient."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    user = User(
        id=1,
        email="analyst@lumen.ai",
        hashed_password=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()

    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"sub": "1", "email": "analyst@lumen.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        yield client, headers, db

    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


def _parse_sse_events(raw_sse_text: str) -> list[dict]:
    """Parse raw SSE text into a list of parsed JSON event payloads."""
    events = []
    lines = raw_sse_text.strip().split("\n")
    for line in lines:
        if line.startswith("data: "):
            payload = line[6:].strip()
            if payload:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(payload))
    return events


def test_six_core_benchmark_questions(agent_test_env) -> None:
    """Verify all six required benchmark questions return correct values aligned with GROUND_TRUTH."""
    client, headers, _ = agent_test_env

    # 1. Create a session
    sess_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Benchmark Suite"}, headers=headers
    )
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["id"]

    benchmarks = [
        # (Question, Expected ground truth substrings)
        (
            "Which region generated the highest revenue?",
            ["North America", "$25,585,262.08"],
        ),
        (
            "Show monthly sales trends.",
            ["Monthly sales trend", "March 2024"],
        ),
        (
            "Which products are underperforming?",
            ["lowest revenue products", "PROD-020", "$33,947.23"],
        ),
        (
            "What are the top five customers?",
            ["top customers", "CUST-0512", "$7,757,525.61"],
        ),
        (
            "Generate SQL for this analysis.",
            ["SELECT", "revenue", "GROUP BY", "Pandas Equivalent"],
        ),
        (
            "Detect anomalies in the dataset.",
            ["5 giant outlier orders", "ORD-OUT-01", "ORD-OUT-05"],
        ),
    ]

    for question, expected_fragments in benchmarks:
        resp = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": question},
            headers=headers,
        )
        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        assert len(events) >= 5, f"Expected full SSE lifecycle for question: {question}"

        # Find final event
        final_events = [e for e in events if e.get("event_type") == "final"]
        assert len(final_events) == 1, f"Missing final event for: {question}"
        answer = final_events[0]["payload"]["direct_answer"]

        for fragment in expected_fragments:
            assert fragment in answer, (
                f"Expected '{fragment}' in answer for '{question}'. Got: {answer}"
            )


def test_followup_reference_resolution(agent_test_env) -> None:
    """Verify follow-up question 'now by month' resolves context from previous turn."""
    client, headers, _ = agent_test_env

    sess_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Followup Test"}, headers=headers
    )
    session_id = sess_resp.json()["id"]

    # Turn 1: Initial query
    resp1 = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Which region generated the highest revenue?"},
        headers=headers,
    )
    assert resp1.status_code == 200

    # Turn 2: Contextual follow-up
    resp2 = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "now by month"},
        headers=headers,
    )
    assert resp2.status_code == 200
    events = _parse_sse_events(resp2.text)

    # Route event must reflect resolved query
    route_event = [e for e in events if e.get("event_type") == "route"][0]
    assert "month" in route_event["payload"]["resolved_question"].lower()

    final_event = [e for e in events if e.get("event_type") == "final"][0]
    answer = final_event["payload"]["direct_answer"]
    assert "Monthly sales trend" in answer


def test_sse_ordering_and_event_lifecycle(agent_test_env) -> None:
    """Verify strict chronological sequence of SSE event types."""
    client, headers, _ = agent_test_env

    sess_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Ordering Test"}, headers=headers
    )
    session_id = sess_resp.json()["id"]

    resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Which region generated the highest revenue?"},
        headers=headers,
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    event_types = [e["event_type"] for e in events]

    # Verify event types exist in correct chronological order
    expected_order = [
        "route",
        "plan",
        "step_start",
        "step_result",
        "verify",
        "chart",
        "token",
        "final",
        "done",
    ]
    indices = []
    for et in expected_order:
        if et in event_types:
            indices.append(event_types.index(et))

    assert indices == sorted(indices), f"Event types not in chronological order: {event_types}"


def test_clarify_lane_options(agent_test_env) -> None:
    """Verify ambiguous prompt routes to clarify lane and returns tappable options."""
    client, headers, _ = agent_test_env

    sess_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Clarify Test"}, headers=headers
    )
    session_id = sess_resp.json()["id"]

    resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "sales"},
        headers=headers,
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)

    route_event = [e for e in events if e.get("event_type") == "route"][0]
    assert route_event["payload"]["lane"] == "clarify"

    final_event = [e for e in events if e.get("event_type") == "final"][0]
    options = final_event["payload"].get("clarification_options", [])
    assert len(options) >= 2
    assert "Highest revenue regions" in options


def test_evidence_ledger_endpoint_inspection(agent_test_env) -> None:
    """Verify GET /api/v1/chat/messages/{id}/evidence returns the recorded Evidence Ledger."""
    client, headers, _ = agent_test_env

    sess_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Ledger Inspection"}, headers=headers
    )
    session_id = sess_resp.json()["id"]

    # Send message to populate ledger
    resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Which region generated the highest revenue?"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Retrieve session history to find message IDs
    history_resp = client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert history_resp.status_code == 200
    messages = history_resp.json()["messages"]
    asst_msgs = [m for m in messages if m["role"] == "assistant"]
    assert len(asst_msgs) == 1
    asst_id = asst_msgs[0]["id"]

    # Inspect evidence ledger endpoint
    evidence_resp = client.get(f"/api/v1/chat/messages/{asst_id}/evidence", headers=headers)
    assert evidence_resp.status_code == 200
    ledger_data = evidence_resp.json()
    assert ledger_data["verified"] is True
    assert ledger_data["confidence"] == "High"
    assert len(ledger_data["steps"]) >= 1
