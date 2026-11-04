"""Semantic layer catalog: compact, prompt-friendly schema summary and business metrics."""

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Dataset, MetricDefinition


class SemanticCatalogBuilder:
    """Constructs LLM-facing compact schema representations and manages user business metrics."""

    HEURISTIC_DESCRIPTIONS: dict[str, str] = {
        "order_id": "Unique primary identifier for the sales order transaction",
        "order_date": "Calendar date when the purchase order was placed (YYYY-MM-DD)",
        "customer_id": "Foreign reference key to the customer account profile",
        "product_id": "Foreign reference key identifying the purchased SKU or product",
        "region": "Geographic sales territory (e.g. North America, EMEA, APAC, LATAM)",
        "quantity": "Total number of product units ordered",
        "unit_price": "Base unit price of the product item prior to discounting",
        "discount": "Promotional percentage discount applied to the transaction line item",
        "revenue": "Net sales revenue computed as SUM(quantity * unit_price * (1 - discount))",
        "company_name": "Legal business entity or organization name",
        "segment": "Commercial customer tier (Enterprise, Mid-Market, SMB)",
        "category": "High-level merchandise category classification",
    }

    def infer_column_description(self, col_name: str, dtype: str) -> str:
        """Derive readable description using heuristic mapping or generative inference."""
        cleaned = col_name.lower().strip()
        if cleaned in self.HEURISTIC_DESCRIPTIONS:
            return self.HEURISTIC_DESCRIPTIONS[cleaned]
        for key, desc in self.HEURISTIC_DESCRIPTIONS.items():
            if key in cleaned:
                return desc
        return f"Data attribute '{col_name}' of type {dtype}"

    def build_compact_catalog(
        self,
        user_id: int,
        db: Session,
        relationships: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Produce the compact schema dictionary presented to LLM planners."""
        datasets = db.query(Dataset).filter(Dataset.user_id == user_id).all()
        user_metrics = db.query(MetricDefinition).filter(MetricDefinition.user_id == user_id).all()

        tables_dict: dict[str, Any] = {}
        for ds in datasets:
            cols_dict: dict[str, str] = {}
            for col in ds.columns:
                cols_dict[col.sanitized_name] = f"{col.data_type} ({col.description or ''})"

            tables_dict[ds.duckdb_table_name] = {
                "display_name": ds.name,
                "row_count": ds.row_count,
                "columns": cols_dict,
            }

        metrics_dict: dict[str, str] = {
            m.name: m.expression for m in user_metrics
        }
        if "revenue" not in metrics_dict:
            metrics_dict["revenue"] = "SUM(quantity * unit_price * (1 - discount))"

        return {
            "tables": tables_dict,
            "metrics": metrics_dict,
            "relationships": relationships or [],
        }
