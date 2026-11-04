"""ECharts neutral specification generator picking chart types from data shape."""

from typing import Any, Literal

ChartType = Literal["line", "bar", "pie", "scatter", "forecast"]


class ChartTool:
    """Generates Apache ECharts neutral JSON specifications based on data shape."""

    def pick_chart_type(self, columns: list[str], sample_data: list[dict[str, Any]]) -> ChartType:
        """Heuristic selector: time->line, share->pie, comparison->bar, correlation->scatter."""
        col_names = " ".join(columns).lower()
        if "date" in col_names or "month" in col_names or "year" in col_names:
            return "line"
        if "share" in col_names or "percentage" in col_names or "ratio" in col_names:
            return "pie"
        if len(columns) == 2 and any(k in col_names for k in ["price", "quantity", "discount"]):
            return "scatter"
        return "bar"

    def build_spec(
        self,
        title: str,
        columns: list[str],
        data: list[dict[str, Any]],
        chart_type: ChartType | None = None,
    ) -> dict[str, Any]:
        """Produce ECharts options payload."""
        selected_type = chart_type or self.pick_chart_type(columns, data)
        return {
            "title": {"text": title},
            "type": selected_type,
            "xAxis": {"type": "category", "data": [d.get(columns[0]) for d in data[:20]]}
            if columns
            else {},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "data": [
                        d.get(columns[1] if len(columns) > 1 else columns[0]) for d in data[:20]
                    ],
                    "type": selected_type if selected_type != "forecast" else "line",
                }
            ],
        }
