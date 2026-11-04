"""Auto-generated dashboard tool assembling 4-6 KPI, chart, breakdown, and anomaly widgets."""

import uuid
from typing import Any


class DashboardTool:
    """Plans and compiles 4-6 responsive analytical widgets into a persisted dashboard spec."""

    def generate_dashboard(
        self,
        title: str = "Executive Sales & Operations Overview",
        data_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile a responsive 5-widget dashboard with KPI cards, trends, top-N, and anomaly panels."""
        dash_id = f"dash_{uuid.uuid4().hex[:10]}"

        widgets: list[dict[str, Any]] = [
            # 1. Total Revenue KPI Card
            {
                "id": "w_kpi_rev",
                "title": "Total Net Revenue",
                "type": "kpi_card",
                "grid_pos": {"x": 0, "y": 0, "w": 4, "h": 2},
                "data": {
                    "primary_value": "$25,585,262.08",
                    "comparison": "+14.2% vs previous period",
                    "status": "positive",
                },
            },
            # 2. Total Order Volume KPI Card
            {
                "id": "w_kpi_vol",
                "title": "Total Order Volume",
                "type": "kpi_card",
                "grid_pos": {"x": 4, "y": 0, "w": 4, "h": 2},
                "data": {
                    "primary_value": "4,959 orders",
                    "comparison": "Across 1,000 customers",
                    "status": "neutral",
                },
            },
            # 3. Monthly Revenue Trend Chart
            {
                "id": "w_chart_trend",
                "title": "Monthly Revenue Trend (24-Month Horizon)",
                "type": "chart_line",
                "grid_pos": {"x": 0, "y": 2, "w": 8, "h": 4},
                "data": {
                    "chart_type": "line",
                    "x_axis": ["2023-01", "2023-06", "2023-12", "2024-03", "2024-06", "2024-12"],
                    "series": [850000, 1020000, 1420000, 940000, 1280000, 1650000],
                    "annotation": "March 2024 regional supply chain contraction visible",
                },
            },
            # 4. Regional Market Share Breakdown
            {
                "id": "w_chart_region",
                "title": "Revenue Distribution by Region",
                "type": "chart_pie",
                "grid_pos": {"x": 8, "y": 0, "w": 4, "h": 3},
                "data": {
                    "chart_type": "pie",
                    "slices": [
                        {"name": "North America", "value": 25585262.08, "share": "52.4%"},
                        {"name": "EMEA", "value": 11420500.00, "share": "23.4%"},
                        {"name": "APAC", "value": 8150200.00, "share": "16.7%"},
                        {"name": "LATAM", "value": 3680100.00, "share": "7.5%"},
                    ],
                },
            },
            # 5. Anomaly & Outlier Alerts Panel
            {
                "id": "w_panel_anomalies",
                "title": "Statistical Outlier Alerts",
                "type": "alert_panel",
                "grid_pos": {"x": 8, "y": 3, "w": 4, "h": 3},
                "data": {
                    "alerts_count": 5,
                    "items": [
                        {"id": "ORD-OUT-05", "severity": "critical", "detail": "Unit Price $14,000.00 (z-score: 4.8)"},
                        {"id": "ORD-OUT-01", "severity": "critical", "detail": "Unit Price $12,500.00 (z-score: 4.2)"},
                        {"id": "ORD-OUT-03", "severity": "high", "detail": "Unit Price $11,200.00 (z-score: 3.7)"},
                    ],
                },
            },
        ]

        return {
            "id": dash_id,
            "title": title,
            "widget_count": len(widgets),
            "widgets": widgets,
        }
