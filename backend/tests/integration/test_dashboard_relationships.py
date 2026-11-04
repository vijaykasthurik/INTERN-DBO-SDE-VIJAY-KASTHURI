from pathlib import Path

import duckdb

from app.tools.dashboard_tool import DashboardTool


def test_sample_relationship_widgets_and_fanout(tmp_path):
    warehouse = str(tmp_path / "joined.duckdb")
    con = duckdb.connect(warehouse)
    samples = Path(__file__).resolve().parents[3] / "sample_data"
    for table in ("sales", "customers", "products"):
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto(?)", [str(samples / f"{table}.csv")])
    con.close()
    dashboard = DashboardTool().generate_dashboard(db_path=warehouse)
    joined = [w for w in dashboard["widgets"] if w["id"].startswith("join_")]
    assert len(joined) >= 2
    assert any("segment" in w["data"]["sql"] for w in joined)
    assert any("category" in w["data"]["sql"] for w in joined)
    assert all(w["data"]["join_fanout_check"]["source_rows"] == w["data"]["join_fanout_check"]["joined_rows"] for w in joined)
    con = duckdb.connect(warehouse)
    con.execute("INSERT INTO customers SELECT * FROM customers")
    con.execute("INSERT INTO products SELECT * FROM products")
    con.close()
    refused = DashboardTool().generate_dashboard(db_path=warehouse)
    assert refused["relationships_used"] == []
    assert "Side-by-side" in refused["explanation"]


def test_unrelated_files_remain_independent(tmp_path):
    warehouse = str(tmp_path / "independent.duckdb")
    con = duckdb.connect(warehouse)
    con.execute("CREATE TABLE first AS SELECT 'a' AS key_a, 7 AS revenue")
    con.execute("CREATE TABLE second AS SELECT 'b' AS key_b, 9 AS amount")
    con.close()
    dashboard = DashboardTool().generate_dashboard(db_path=warehouse)
    assert dashboard["relationships_used"] == []
    assert "Side-by-side" in dashboard["explanation"]
