"""Integration tests for Phase 5: Advanced tools, Skeptic Verifier, Semantic Cache, and Budget Governor."""

import pathlib

import pandas as pd
import pytest

from app.agent.cache import VerifiedAnswerCache
from app.agent.engine import AgentEngine
from app.agent.ledger import EvidenceLedger
from app.agent.verifier import Verifier
from app.llm.budget import BudgetGovernor
from app.tools.anomaly_tool import AnomalyTool
from app.tools.dashboard_tool import DashboardTool
from app.tools.forecast_tool import ForecastTool
from app.tools.hypothesis_tool import HypothesisTool


def test_anomaly_tool_detects_seeded_truths() -> None:
    """Verify AnomalyTool detects the 5 seeded outliers and duplicate block in sales.csv."""
    sample_csv = pathlib.Path(__file__).resolve().parents[3] / "sample_data" / "sales.csv"
    assert sample_csv.exists(), f"Sample sales file not found at {sample_csv}"

    df = pd.read_csv(sample_csv)
    tool = AnomalyTool()
    result = tool.detect_anomalies(df, target_column="unit_price", id_column="order_id")

    # 1. Verify Outliers
    outliers = result["outliers"]
    assert len(outliers) == 5, f"Expected exactly 5 outliers, got {len(outliers)}"

    outlier_ids = {o["id"] for o in outliers}
    expected_ids = {"ORD-OUT-01", "ORD-OUT-02", "ORD-OUT-03", "ORD-OUT-04", "ORD-OUT-05"}
    assert outlier_ids == expected_ids, f"Outlier IDs mismatch: {outlier_ids} vs {expected_ids}"

    # Verify per-flag explanation payload
    for o in outliers:
        assert len(o["methods_fired"]) >= 1
        assert "typical_range" in o
        assert "peer_group_comparison" in o
        assert "reason" in o
        assert o["value"] >= 8000.0

    # 2. Verify Duplicate Block
    duplicates = result["duplicates"]
    assert len(duplicates) == 3, f"Expected 3 duplicate block entries, got {len(duplicates)}"
    assert result["summary"]["duplicate_rows"] == 3


def test_forecast_tool_mape_and_short_history_refusal() -> None:
    """Verify ForecastTool reports backtest MAPE and refuses when history is under 6 periods."""
    tool = ForecastTool()

    # 1. Refusal on too short history (< 6 periods)
    short_history = [12000.0, 14000.0, 13500.0, 15000.0]
    refusal_result = tool.generate_forecast(short_history)
    assert refusal_result["success"] is False
    assert "Insufficient historical observations" in refusal_result["error"]
    assert len(refusal_result["predictions"]) == 0

    # 2. Successful forecast with backtest MAPE
    # 24 periods representing monthly sales
    monthly_data = [
        100000.0, 105000.0, 110000.0, 108000.0, 115000.0, 120000.0,
        125000.0, 122000.0, 130000.0, 135000.0, 140000.0, 150000.0,
        145000.0, 152000.0, 158000.0, 155000.0, 162000.0, 168000.0,
        175000.0, 172000.0, 180000.0, 188000.0, 195000.0, 210000.0,
    ]
    forecast_result = tool.generate_forecast(monthly_data, periods_ahead=3)
    assert forecast_result["success"] is True
    assert len(forecast_result["predictions"]) == 3

    diagnostics = forecast_result["model_diagnostics"]
    assert diagnostics is not None
    assert "backtest_mape" in diagnostics
    assert "%" in diagnostics["backtest_mape"] or "N/A" not in diagnostics["backtest_mape"]

    for pred in forecast_result["predictions"]:
        assert pred["predicted"] > 0
        assert pred["upper_bound"] > pred["lower_bound"]


def test_hypothesis_tool_ranks_march_dip() -> None:
    """Verify HypothesisTool generates candidate causes and identifies the March EMEA dip."""
    tool = HypothesisTool()
    result = tool.investigate_drop(target_period="2024-03", target_region="EMEA")

    assert result["target_period"] == "2024-03"
    assert result["target_region"] == "EMEA"
    assert "EMEA" in result["primary_cause"]

    ranked = result["ranked_hypotheses"]
    assert len(ranked) >= 4

    # Top hypothesis must be regional supply disruption with highest explained variance
    top_cause = ranked[0]
    assert top_cause["rank"] == 1
    assert "EMEA" in top_cause["hypothesis"]
    assert top_cause["explained_variance_ratio"] == 0.84
    assert top_cause["status"] == "confirmed"

    # Refuted hypothesis (discounting erosion) has low explained variance
    refuted = [h for h in ranked if h["status"] == "refuted"]
    assert len(refuted) >= 1
    assert refuted[0]["explained_variance_ratio"] < 0.10


def test_dashboard_tool_widgets_use_live_duckdb_data(tmp_path) -> None:
    """Verify dashboard figures are computed from a real tenant database and never defaults."""
    import duckdb

    tool = DashboardTool()
    db_path = str(tmp_path / "dashboard.duckdb")
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE sales (month VARCHAR, region VARCHAR, revenue DOUBLE)")
    con.execute("INSERT INTO sales VALUES ('2025-01', 'West', 12.5), ('2025-02', 'East', 7.5)")
    con.close()
    dash = tool.generate_dashboard(title="Q1 Executive Board Deck", db_path=db_path)

    assert "id" in dash
    assert dash["title"] == "Q1 Executive Board Deck"
    assert 4 <= dash["widget_count"] <= 6

    widgets = dash["widgets"]
    assert len(widgets) == dash["widget_count"]

    widget_types = {w["type"] for w in widgets}
    assert "kpi_card" in widget_types
    assert "chart_line" in widget_types
    assert "alert_panel" in widget_types
    totals = next(w for w in widgets if w["id"] == "w_total")
    assert totals["data"]["numeric_val"] == 20.0
    assert "2025-01" in next(w for w in widgets if w["id"] == "w_trend")["data"]["x_axis"]
    assert "25,585,262" not in str(widgets)


def test_verifier_catches_and_redacts_ungrounded_numbers() -> None:
    """Verify Verifier skeptic catches ungrounded numbers and redacts them from final answers."""
    verifier = Verifier()
    ledger = EvidenceLedger()

    # Step records real ground truth numbers
    ledger.record_step(
        step_id="step_1",
        tool="sql_tool",
        code="SELECT region, SUM(revenue) FROM sales GROUP BY region;",
        result_preview=[{"region": "North America", "revenue": 1482900.00}],
        row_count=1,
        runtime_ms=12.5,
        status="success",
    )

    # Draft answer contains 1 legitimate number ($1,482,900.00) and 1 invented number ($987,654.32)
    draft = "North America revenue was $1,482,900.00 while unverified secondary bookings were $987,654.32."

    res = verifier.verify(draft, ledger)

    assert 987654.32 in res.ungrounded_numbers
    assert res.grounded_numbers_ratio < 1.0
    assert "[UNGROUNDED_NUMBER_REMOVED]" in res.sanitized_answer
    assert "$1,482,900.00" in res.sanitized_answer
    assert any("Ungrounded numbers detected" in r for r in res.reasons)


def test_verifier_detects_join_fanout() -> None:
    """Verify Verifier flags excessive join fan-out as low confidence and recommends re-plan."""
    verifier = Verifier()
    ledger = EvidenceLedger()

    # Simulate catastrophic cartesian product
    ledger.record_step(
        step_id="step_join",
        tool="sql_tool",
        code="SELECT * FROM sales s JOIN customers c ON 1=1;",
        result_preview=[{"col": "val"}],
        row_count=95000,
        runtime_ms=450.0,
        status="success",
    )

    res = verifier.verify("Draft summary of customers", ledger)
    assert any("JOIN fan-out detected" in r for r in res.reasons)
    assert res.replan_recommended is True


def test_verified_answer_cache_lifecycle_and_invalidation() -> None:
    """Verify cache stores High/Medium confidence answers and invalidates on schema changes."""
    cache = VerifiedAnswerCache(default_ttl_sec=3600)

    # 1. High confidence answers are cached
    stored = cache.put(
        question="Which region generated highest revenue?",
        answer_payload={"direct_answer": "North America", "revenue": 1482900.0},
        confidence="High",
        schema_hash="schema_v1",
    )
    assert stored is True

    # 2. Low confidence answers are REJECTED (Rule P2)
    low_stored = cache.put(
        question="Uncertain metric estimate",
        answer_payload={"direct_answer": "Estimated $50k"},
        confidence="Low",
        schema_hash="schema_v1",
    )
    assert low_stored is False

    # 3. Cache retrieval hits
    key = cache.generate_cache_key("Which region generated highest revenue?", "schema_v1")
    cached_payload = cache.get(key)
    assert cached_payload is not None
    assert cached_payload["direct_answer"] == "North America"
    assert cache.hits == 1

    # 4. Invalidation clears cache entries for modified schema
    removed = cache.invalidate_schema("schema_v1")
    assert removed == 1

    # Now retrieval misses
    miss_payload = cache.get(key)
    assert miss_payload is None
    assert cache.misses == 1


@pytest.mark.asyncio
async def test_budget_governor_enforces_step_cap() -> None:
    """Verify BudgetGovernor caps steps and engine outputs honest partial-analysis notice."""
    governor = BudgetGovernor(max_steps=1)
    governor.record_step(tokens=100)  # Reaches 1 step limit

    engine = AgentEngine()
    events = []
    async for event in engine.run(
        question="Generate extensive 20-step analysis across all dimensions",
        session_id="test_sess",
        user_id=1,
        trace_id="tr_budget_01",
        governor=governor,
    ):
        events.append(event)

    event_types = [e.event_type for e in events]
    assert "final" in event_types
    assert "done" in event_types

    final_event = next(e for e in events if e.event_type == "final")
    assert final_event.payload.get("partial_analysis") is True
    assert "Budget limit reached" in final_event.payload.get("direct_answer", "") or "budget constraints" in final_event.payload.get("direct_answer", "")
