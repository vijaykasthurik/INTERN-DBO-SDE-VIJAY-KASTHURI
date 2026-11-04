"""Integration tests for Phase 4: Agent engine PEVN pipeline, SSE streaming, and Ground Truth benchmarks."""

import contextlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.models import Base, User
from app.db.session import get_db
from app.main import create_app
from app.data.ingestion import DataIngestionPipeline
from app.api.chat import _AGENT_ENGINE


@pytest.fixture
def agent_test_env(monkeypatch, tmp_path):
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

    monkeypatch.setattr(DataIngestionPipeline, "get_user_db_path", lambda _self, user_id: str(tmp_path / f"user-{user_id}.duckdb"))
    _AGENT_ENGINE.cache._store.clear()

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
        sample_dir = Path(__file__).resolve().parents[3] / "sample_data"
        files = [("files", (name, (sample_dir / name).read_bytes(), "text/csv")) for name in ("sales.csv", "customers.csv", "products.csv")]
        upload_response = client.post("/api/v1/upload", files=files, headers=headers)
        assert upload_response.status_code == 201
        yield client, headers, db

    app.dependency_overrides.clear()
    _AGENT_ENGINE.cache._store.clear()
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
            ["region: North America", "25,585,262.076"],
        ),
        (
            "Show monthly sales trends.",
                ["month: 2024-05", "revenue:"],
        ),
        (
            "Which products are underperforming?",
            ["product_id: PROD-020", "revenue:"],
        ),
        (
            "What are the top five customers?",
            ["customer_id: CUST-0512", "total_spend:"],
        ),
        (
            "Generate SQL for this analysis.",
                    ["Executed DuckDB SQL", "SELECT", "LIMIT 1000"],
        ),
        (
            "Detect anomalies in the dataset.",
            ["anomaly_tool result", "outliers_detected"],
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
    assert "month: 2024-05" in answer


def test_dataset_pagination_dashboard_scopes_and_cascade_delete(agent_test_env) -> None:
    """Dataset pages and dashboard scopes use uploaded rows; deletion removes all references."""
    client, headers, _ = agent_test_env
    datasets_response = client.get("/api/v1/datasets", headers=headers)
    assert datasets_response.status_code == 200
    datasets = datasets_response.json()
    assert len(datasets) == 3

    dataset = datasets[0]
    dataset_id = dataset["id"]
    preview = client.get(f"/api/v1/datasets/{dataset_id}/rows?offset=0&limit=2", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["total_rows"] == dataset["row_count"]
    assert len(preview.json()["rows"]) == 2
    assert set(preview.json()["rows"][0]) == set(preview.json()["columns"])
    rerun = client.post(
        "/api/v1/chat/execute",
        json={"sql": f'SELECT COUNT(*) AS n FROM "{dataset["table_name"]}"'},
        headers=headers,
    )
    assert rerun.status_code == 200
    assert rerun.json()["rows"][0]["n"] == dataset["row_count"]
    rejected = client.post(
        "/api/v1/chat/execute", json={"sql": "DROP TABLE sales"}, headers=headers
    )
    assert rejected.status_code == 400

    combined = client.post("/api/v1/dashboards/generate", json={"scope": "combined"}, headers=headers)
    per_file = client.post("/api/v1/dashboards/generate", json={"scope": str(dataset_id)}, headers=headers)
    assert combined.status_code == 201 and combined.json()["scope"] == "combined"
    assert per_file.status_code == 201 and per_file.json()["scope"] == dataset["table_name"]
    assert combined.json()["widgets"][0]["data"]["primary_value"] == "3 files"

    deleted = client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/datasets/{dataset_id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/datasets/{dataset_id}/rows?offset=0&limit=2", headers=headers).status_code == 404
    after_delete = client.get("/api/v1/datasets", headers=headers).json()
    assert len(after_delete) == 2
    refreshed = client.post("/api/v1/dashboards/generate", json={"scope": "combined"}, headers=headers)
    assert refreshed.status_code == 201
    assert refreshed.json()["widgets"][0]["data"]["primary_value"] == "2 files"

    session = client.post("/api/v1/chat/sessions", json={"title": "Post-delete audit"}, headers=headers)
    answer_events = client.post(
        f"/api/v1/chat/sessions/{session.json()['id']}/messages",
        json={"content": "What is in these files? Explain each file."},
        headers=headers,
    )
    final = next(event for event in _parse_sse_events(answer_events.text) if event.get("event_type") == "final")
    assert f"### {dataset['table_name']}\n" not in final["payload"]["direct_answer"]
    overview = next(event for event in _parse_sse_events(answer_events.text) if event.get("event_type") == "step_result" and event["payload"].get("tool") == "overview_tool")
    assert dataset["table_name"] not in {table["table"] for table in overview["payload"]["result_preview"]["tables"]}


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


def test_dataset_rename_replace_search_order_and_report_cascade(agent_test_env):
    client, headers, db = agent_test_env
    from app.db.models import DatasetColumn, ReportArtifact, MetricDefinition
    datasets = client.get("/api/v1/datasets", headers=headers).json()
    dataset = next(item for item in datasets if item["table_name"] == "sales")
    dataset_id = dataset["id"]
    renamed = client.patch(f"/api/v1/datasets/{dataset_id}", json={"name":"Sales ledger"}, headers=headers)
    assert renamed.status_code == 200 and renamed.json()["name"] == "Sales ledger"
    rows = client.get(f"/api/v1/datasets/{dataset_id}/rows?q=North%20America&sort=unit_price&direction=desc&limit=2", headers=headers)
    assert rows.status_code == 200
    assert len(rows.json()["rows"]) == 2
    assert rows.json()["rows"][0]["unit_price"] >= rows.json()["rows"][1]["unit_price"]
    assert rows.json()["column_types"]["unit_price"]
    assert client.get(f"/api/v1/datasets/{dataset_id}/rows?sort=missing",headers=headers).status_code == 422
    dashboard = client.post("/api/v1/dashboards/generate",json={"scope":str(dataset_id)},headers=headers).json()
    order = [widget["id"] for widget in dashboard["widgets"]][::-1]
    assert client.patch(f"/api/v1/dashboards/{dashboard['id']}/order",json={"widget_ids":order},headers=headers).status_code == 200
    regenerated = client.post("/api/v1/dashboards/generate",json={"scope":str(dataset_id)},headers=headers).json()
    assert [widget["id"] for widget in regenerated["widgets"]] == order
    report = client.post("/api/v1/reports/export",json={"dashboard":dashboard,"format":"md"},headers=headers)
    assert report.status_code == 201
    report_url = report.json()["download_url"]
    assert db.query(ReportArtifact).count() == 1
    assert client.post("/api/v1/reports/export",json={"dashboard":{"id":"fake"},"format":"md"},headers=headers).status_code == 404
    replacement = client.post(f"/api/v1/datasets/{dataset_id}/replace",files={"file":("replacement.csv",b"customer_id,revenue\nA,10\nB,20\n","text/csv")},headers=headers)
    assert replacement.status_code == 200
    assert replacement.json()["id"] == dataset_id and replacement.json()["row_count"] == 2
    assert replacement.json()["name"] == "Sales ledger"
    assert db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).count() == 2
    assert db.query(MetricDefinition).filter(MetricDefinition.dataset_id == dataset_id).count() == 0
    assert db.query(ReportArtifact).count() == 0
    assert client.get(report_url,headers=headers).status_code == 404
    assert client.get(f"/api/v1/dashboards/{dashboard['id']}",headers=headers).status_code == 404
    assert client.post("/api/v1/auth/clear-data",headers=headers).status_code == 200
    assert client.get("/api/v1/datasets",headers=headers).json() == []
    assert db.query(DatasetColumn).count() == 0
