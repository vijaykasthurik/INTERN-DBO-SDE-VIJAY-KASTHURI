"""Statistical profiler and data quality auditor tests against GROUND_TRUTH."""

from pathlib import Path

import pytest

from app.data.ingestion import DataIngestionPipeline
from app.data.profiler import DatasetProfiler
from app.data.quality import QualityAuditor


def test_profiler_and_quality_on_sample_data(tmp_path):
    """Verify statistical profiling and data quality audit on sales.csv matches GROUND_TRUTH.md."""
    sales_path = Path(__file__).resolve().parents[3] / "sample_data" / "sales.csv"
    if not sales_path.exists():
        sales_path = Path("sample_data/sales.csv")
        pytest.skip("sample_data/sales.csv not yet generated")

    with open(sales_path, "rb") as f:
        content = f.read()

    pipeline = DataIngestionPipeline(data_dir=str(tmp_path))
    ingest_res = pipeline.ingest_csv(user_id=1, filename="sales.csv", content_bytes=content)

    db_path = ingest_res["db_path"]
    table_name = ingest_res["table_name"]

    profiler = DatasetProfiler()
    profiles = profiler.profile_table(db_path, table_name)

    # 1. Total rows matches (~4959)
    assert ingest_res["row_count"] > 4900

    # 2. Verify profiles include all columns
    col_names = [p["column_name"] for p in profiles]
    assert "order_id" in col_names
    assert "region" in col_names
    assert "unit_price" in col_names
    assert "discount" in col_names

    # 3. Verify discount contains expected nulls
    discount_prof = next(p for p in profiles if p["column_name"] == "discount")
    assert discount_prof["null_count"] > 0

    # 4. Verify quality audit identifies duplicates and missing values
    auditor = QualityAuditor()
    quality = auditor.evaluate_table_quality(db_path, table_name)

    assert 80.0 <= quality["score"] <= 99.0
    categories = [i["category"] for i in quality["issues"]]
    assert "missing_values" in categories
    assert "duplicates" in categories
