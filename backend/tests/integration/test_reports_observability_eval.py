"""Integration tests for Phase 6: Reports export (PDF + Markdown), Prometheus metrics, and tracing."""

import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.models import Base, ChatMessage, ChatSession, User
from app.db.models import ExecutionTrace as DBExecutionTrace
from app.db.session import get_db
from app.main import create_app
from app.observability.tracing import ExecutionTrace, TraceManager
from app.reports.builder import ReportBuilder
from app.reports.markdown import MarkdownReportExporter
from app.reports.pdf import PDFReportExporter


def test_markdown_and_pdf_report_generation(tmp_path: Path) -> None:
    """Verify ReportBuilder, MarkdownReportExporter, and PDFReportExporter output valid reports."""
    builder = ReportBuilder()
    md_exporter = MarkdownReportExporter()
    pdf_exporter = PDFReportExporter()

    mock_messages = [
        {
            "role": "assistant",
            "content": "North America generated the highest total revenue at $25,585,262.08.",
            "evidence": {
                "verified": True,
                "confidence": "High",
                "verification": {"confidence": "High", "reasons": ["Query result matched its Evidence Ledger values."]},
                "steps": [
                    {
                        "tool": "sql_tool",
                        "code": "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS revenue FROM sales GROUP BY region ORDER BY revenue DESC;",
                        "runtime_ms": 15.4,
                        "row_count": 4,
                        "result_preview": [{"region": "West", "revenue": 12.5}, {"region": "East", "revenue": 7.5}],
                    },
                    {"tool": "chart_tool", "code": "chart_tool.build_spec", "runtime_ms": 1.2, "row_count": 2,
                     "result_preview": {"title": "Revenue by Region", "data": {"x_axis": ["West", "East"], "series": [12.5, 7.5]}}},
                ],
            },
        }
    ]

    report_data = builder.build_report_data(
        session_id="sess_test_report",
        messages=mock_messages,
        title="Q4 Financial Review",
    )

    # 1. Test Markdown Export
    md_text = md_exporter.render_markdown(report_data)
    assert "# Q4 Financial Review" in md_text
    assert "SELECT region" in md_text
    assert "Executive Summary" in md_text
    assert "Data Health & Quality Audit" in md_text
    assert "Skeptic Verifier Audit Trail" in md_text

    # 2. Test PDF Export
    pdf_path = str(tmp_path / "test_report.pdf")
    pdf_exporter.render_pdf(report_data, pdf_path)

    assert os.path.exists(pdf_path)
    file_size = os.path.getsize(pdf_path)
    assert file_size > 1000, f"Expected a non-empty PDF report, got {file_size} bytes"

    # Verify PDF magic header
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-", "Invalid PDF file header format"


def test_reports_api_endpoints() -> None:
    """Verify POST /api/v1/reports/export and GET /api/v1/reports/download/{file} endpoints."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    user = User(id=1, email="cfo@lumen.ai", hashed_password=hash_password("Pass123!"), is_active=True)
    db.add(user)
    session = ChatSession(id="sess_board_deck", user_id=1, title="Board Executive Report")
    db.add(session)
    db.add(ChatMessage(
        id="msg_board_deck", session_id=session.id, role="assistant",
        content="West recorded revenue of 12.5 from the executed query.", confidence="High",
        evidence_ledger={"entries": [{"step_id": "step_1", "tool": "sql_tool", "code": "SELECT region, SUM(revenue) AS revenue FROM sales GROUP BY region", "result_preview": [{"region": "West", "revenue": 12.5}], "row_count": 1, "runtime_ms": 2.1, "status": "success"}], "verification": {"confidence": "High", "reasons": ["All cited numbers are grounded."]}},
    ))
    db.commit()

    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"sub": "1", "email": "cfo@lumen.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # 1. Export PDF
        pdf_res = client.post(
            "/api/v1/reports/export",
            json={"session_id": "sess_board_deck", "format": "pdf", "title": "Board Executive Report"},
            headers=headers,
        )
        assert pdf_res.status_code == 201
        pdf_data = pdf_res.json()
        assert pdf_data["format"] == "pdf"
        assert "download_url" in pdf_data

        # Download PDF
        dl_res = client.get(pdf_data["download_url"], headers=headers)
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert dl_res.content[:5] == b"%PDF-"
        from pypdf import PdfReader
        from io import BytesIO
        extracted = "\n".join(page.extract_text() for page in PdfReader(BytesIO(dl_res.content)).pages)
        assert "Lumen" in extracted
        assert "West recorded revenue of 12.5" in extracted
        assert "SELECT region, SUM(revenue) AS revenue FROM sales GROUP BY region" in extracted
        assert "Confidence: High" in extracted

        # 2. Export Markdown
        md_res = client.post(
            "/api/v1/reports/export",
            json={"session_id": "sess_board_deck", "format": "md", "title": "Board Executive Report"},
            headers=headers,
        )
        assert md_res.status_code == 201
        md_data = md_res.json()
        assert md_data["format"] == "md"

        # Download Markdown
        dl_md_res = client.get(md_data["download_url"], headers=headers)
        assert dl_md_res.status_code == 200
        assert "text/markdown" in dl_md_res.headers["content-type"]
        assert "# Board Executive Report" in dl_md_res.text
        assert "West recorded revenue of 12.5" in dl_md_res.text
        assert client.get(pdf_data["download_url"]).status_code == 401

        # 3. List reports
        list_res = client.get("/api/v1/reports", headers=headers)
        assert list_res.status_code == 200
        report_list = list_res.json()
        assert len(report_list) == 2
        report_ids = [r["report_id"] for r in report_list]
        assert pdf_data["report_id"] in report_ids
        assert md_data["report_id"] in report_ids

        # 4. Preview both artifacts (verifying preview payload from the same artifacts)
        pdf_preview_res = client.get(pdf_data["download_url"], headers=headers)
        assert pdf_preview_res.status_code == 200
        assert pdf_preview_res.content.startswith(b"%PDF-")
        md_preview_res = client.get(md_data["download_url"], headers=headers)
        assert md_preview_res.status_code == 200
        assert "West recorded revenue of 12.5" in md_preview_res.text

        # 5. Delete report
        del_res = client.delete(f"/api/v1/reports/{md_data['report_id']}", headers=headers)
        assert del_res.status_code == 204
        # Verify it is no longer listed
        after_del_list = client.get("/api/v1/reports", headers=headers).json()
        assert len(after_del_list) == 1
        assert after_del_list[0]["report_id"] == pdf_data["report_id"]
        # Verify download returns 404
        assert client.get(md_data["download_url"], headers=headers).status_code == 404

    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_trace_manager_persistence() -> None:
    """Verify TraceManager records traces in memory and persists to SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    manager = TraceManager()
    trace = ExecutionTrace(
        trace_id="tr_exec_001",
        user_id=1,
        session_id="sess_trace_test",
        question="Which region generated the highest revenue?",
        lane="analysis",
        provider="mock",
        duration_ms=45.2,
        total_tokens=180,
        cost_usd=0.0,
        cache_hit=False,
        verifier_confidence="High",
    )

    manager.record_trace(trace, db=db)

    # Verify SQLite row created
    db_row = db.query(DBExecutionTrace).filter(DBExecutionTrace.trace_id == "tr_exec_001").first()
    assert db_row is not None
    assert db_row.duration_ms == 45.2
    assert db_row.verifier_confidence == "High"

    # Query via TraceManager
    traces = manager.get_session_traces("sess_trace_test", db=db)
    assert len(traces) == 1
    assert traces[0].trace_id == "tr_exec_001"

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_prometheus_metrics_scrape_endpoint() -> None:
    """Verify GET /metrics returns standard Prometheus telemetry text."""
    app = create_app()
    with TestClient(app) as client:
        # Trigger an endpoint to increment metrics
        client.get("/health")

        # Scrape /metrics
        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "text/plain" in metrics_resp.headers["content-type"]
        body = metrics_resp.text

        # Verify essential Prometheus metric families are present
        assert "lumen_http_requests_total" in body
        assert "lumen_request_duration_seconds" in body
        assert "lumen_llm_calls_total" in body
        assert "lumen_cache_hits_total" in body
