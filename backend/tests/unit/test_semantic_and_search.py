"""Tests for Semantic Catalog, Embedding Search, and Join Key Discovery."""

from pathlib import Path

import pytest

from app.data.embeddings import SemanticEmbeddingStore
from app.data.ingestion import DataIngestionPipeline
from app.data.relationships import RelationshipDetector
from app.tools.search_tool import SearchTool


def test_semantic_search_turnover_maps_to_revenue():
    """Verify that query 'turnover' semantically maps to the 'revenue' column."""
    store = SemanticEmbeddingStore()
    columns = [
        "order_id",
        "order_date",
        "customer_id",
        "product_id",
        "region",
        "revenue",
        "discount",
    ]
    store.fit_terms(columns)

    search_tool = SearchTool(store)
    matches = search_tool.search_schema("turnover", top_k=3)

    assert len(matches) > 0
    top_match_term, top_score = matches[0]
    assert top_match_term == "revenue"
    assert top_score >= 0.8


def test_semantic_search_buyer_maps_to_customer():
    """Verify synonym 'buyer' maps to 'customer_id'."""
    store = SemanticEmbeddingStore()
    columns = ["order_id", "customer_id", "product_id", "quantity", "unit_price"]
    store.fit_terms(columns)

    search_tool = SearchTool(store)
    matches = search_tool.search_schema("buyer", top_k=3)
    assert len(matches) > 0
    top_match = matches[0][0]
    assert "customer" in top_match.lower()


def test_relationship_detection_sales_and_customers(tmp_path):
    """Verify automated detection of customer_id foreign key between sales and customers."""
    base_dir = Path(__file__).resolve().parents[3] / "sample_data"
    sales_path = base_dir / "sales.csv"
    cust_path = base_dir / "customers.csv"
    if not sales_path.exists() or not cust_path.exists():
        sales_path = Path("sample_data/sales.csv")
        cust_path = Path("sample_data/customers.csv")
        pytest.skip("sample data not present")

    pipeline = DataIngestionPipeline(data_dir=str(tmp_path))
    with open(sales_path, "rb") as f1, open(cust_path, "rb") as f2:
        ingest1 = pipeline.ingest_csv(user_id=1, filename="sales.csv", content_bytes=f1.read())
        ingest2 = pipeline.ingest_csv(user_id=1, filename="customers.csv", content_bytes=f2.read())

    db_path = ingest1["db_path"]
    detector = RelationshipDetector()
    edges = detector.detect_table_relationships(
        db_path, [ingest1["table_name"], ingest2["table_name"]]
    )

    assert len(edges) >= 1
    # Check that customer_id join key was detected
    c_edge = next(
        e for e in edges if "customer_id" in e["from_column"] or "customer_id" in e["to_column"]
    )
    assert c_edge["confidence"] >= 0.7
    assert c_edge["overlap_ratio"] >= 0.7
