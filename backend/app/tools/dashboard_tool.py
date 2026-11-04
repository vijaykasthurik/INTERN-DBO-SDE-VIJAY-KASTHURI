"""Dashboard generator tool: plans 4-6 KPI and visual widgets executed in parallel."""

from typing import Any


class DashboardTool:
    """Plans balanced dashboard widgets: KPI cards, line trends, bar breakdowns, and anomalies."""

    def plan_widgets(self, tables_catalog: dict[str, Any]) -> list[dict[str, Any]]:
        """Synthesize 4-6 widget specifications."""
        return [
            {
                "id": "w1",
                "type": "kpi",
                "title": "Total Revenue",
                "query": "SELECT SUM(revenue) FROM sales",
            },
            {
                "id": "w2",
                "type": "trend",
                "title": "Monthly Revenue Trend",
                "query": "SELECT month, SUM(revenue) FROM sales GROUP BY month",
            },
            {
                "id": "w3",
                "type": "breakdown",
                "title": "Revenue by Region",
                "query": "SELECT region, SUM(revenue) FROM sales GROUP BY region",
            },
            {
                "id": "w4",
                "type": "anomaly",
                "title": "Flagged Outliers",
                "query": "SELECT * FROM sales WHERE is_anomaly = true",
            },
        ]
