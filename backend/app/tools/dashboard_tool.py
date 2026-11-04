"""Build dashboard widgets only from live, read-only DuckDB query results."""

import os
import uuid
from typing import Any

import duckdb


class DashboardTool:
    """Compile per-table or side-by-side multi-table dashboards from tenant data."""

    def generate_dashboard(
        self,
        title: str = "Executive Sales & Operations Overview",
        data_summary: dict[str, Any] | None = None,
        db_path: str | None = None,
        scope_table: str | None = None,
    ) -> dict[str, Any]:
        if not db_path or not os.path.exists(db_path):
            raise ValueError("Upload a dataset before generating a dashboard.")
        con = duckdb.connect(db_path, read_only=True)
        try:
            tables = [str(row[0]) for row in con.execute("SHOW TABLES").fetchall()]
            if scope_table:
                if scope_table not in tables:
                    raise ValueError("The selected dataset is no longer available.")
                tables = [scope_table]
            if not tables:
                raise ValueError("Upload a dataset before generating a dashboard.")

            table_summaries: list[dict[str, Any]] = []
            for table in tables:
                columns = con.execute(f'DESCRIBE "{table}"').fetchall()
                names = [str(col[0]) for col in columns]
                types = {str(col[0]): str(col[1]).upper() for col in columns}
                count_result = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
                row_count = int(count_result[0]) if count_result else 0
                numeric = [n for n in names if any(t in types[n] for t in ("INT", "DECIMAL", "DOUBLE", "FLOAT", "REAL"))]
                dates = [n for n in names if any(t in types[n] for t in ("DATE", "TIME")) or "date" in n.lower() or "month" in n.lower()]
                categories = [n for n in names if n not in numeric and n not in dates and not types[n].startswith(("BLOB", "MAP", "STRUCT", "LIST"))]
                summary: dict[str, Any] = {"table": table, "row_count": row_count, "columns": names, "numeric": numeric, "dates": dates, "categories": categories}
                if numeric:
                    measure = next((n for n in numeric if any(word in n.lower() for word in ("revenue", "sales", "amount", "price", "total"))), numeric[0])
                    quoted = f'"{measure}"'
                    aggregate = f'SUM({quoted})'
                    if {"quantity", "unit_price", "discount"}.issubset({n.lower() for n in names}):
                        lookup = {n.lower(): n for n in names}
                        aggregate = f'SUM("{lookup["quantity"]}" * "{lookup["unit_price"]}" * (1 - "{lookup["discount"]}"))'
                        measure = "net_revenue"
                    value_result = con.execute(f'SELECT {aggregate} FROM "{table}"').fetchone()
                    value = value_result[0] if value_result else 0
                    summary.update({"measure": measure, "measure_total": float(value or 0), "measure_sql": f'SELECT {aggregate} AS total FROM "{table}"'})
                    if dates:
                        date_col = dates[0]
                        trend_sql = f'SELECT CAST("{date_col}" AS VARCHAR) AS period, {aggregate} AS value FROM "{table}" GROUP BY period ORDER BY period LIMIT 100'
                        rows = con.execute(trend_sql).fetchall()
                        summary.update({"trend": [{"name": str(r[0]), "value": float(r[1] or 0)} for r in rows], "trend_sql": trend_sql})
                    elif categories:
                        category = categories[0]
                        trend_sql = f'SELECT CAST("{category}" AS VARCHAR) AS name, {aggregate} AS value FROM "{table}" GROUP BY name ORDER BY value DESC LIMIT 20'
                        rows = con.execute(trend_sql).fetchall()
                        summary.update({"breakdown": [{"name": str(r[0]), "value": float(r[1] or 0)} for r in rows], "trend_sql": trend_sql})
                table_summaries.append(summary)
        finally:
            con.close()

        widgets: list[dict[str, Any]] = []
        if len(table_summaries) == 1:
            item = table_summaries[0]
            widgets.append({"id": "w_rows", "title": f"Rows in {item['table']}", "type": "kpi_card", "data": {"primary_value": f"{item['row_count']:,} rows", "numeric_val": item["row_count"], "comparison": f"{len(item['columns'])} columns", "sql": f'SELECT COUNT(*) AS row_count FROM "{item["table"]}"', "row_count": 1}})
            if "measure_total" in item:
                widgets.append({"id": "w_total", "title": f"Total {item['measure']}", "type": "kpi_card", "data": {"primary_value": f"{item['measure_total']:,.2f}", "numeric_val": item["measure_total"], "comparison": f"Computed from {item['table']}", "sql": item["measure_sql"], "row_count": 1}})
                values = item.get("trend") or item.get("breakdown") or []
                if values:
                    widgets.append({"id": "w_trend", "title": f"{item['measure']} by {item['dates'][0] if item.get('trend') else item['categories'][0]}", "type": "chart_line" if item.get("trend") else "chart_pie", "data": {"x_axis": [v["name"] for v in values], "series": [v["value"] for v in values], "slices": values, "annotation": "Computed from the selected dataset.", "sql": item["trend_sql"], "row_count": len(values)}})
            widgets.append({"id": "w_schema", "title": "Dataset schema", "type": "alert_panel", "data": {"alerts_count": 0, "items": [], "annotation": f"Live profile: {item['row_count']:,} rows and {len(item['columns'])} columns. No anomaly scan was run."}})
            scope_label = item["table"]
        else:
            widgets.append({"id": "w_tables", "title": "Files analyzed", "type": "kpi_card", "data": {"primary_value": f"{len(table_summaries)} files", "numeric_val": len(table_summaries), "comparison": "Live summaries from each uploaded file", "row_count": 1}})
            widgets.append({"id": "w_rows", "title": "Rows by file", "type": "chart_pie", "data": {"slices": [{"name": t["table"], "value": t["row_count"]} for t in table_summaries], "sql": "Independent COUNT(*) query per file", "row_count": len(table_summaries)}})
            widgets.append({"id": "w_summary", "title": "Side-by-side file summaries", "type": "alert_panel", "data": {"alerts_count": 0, "items": [{"id": t["table"], "severity": "info", "detail": f"{t['row_count']:,} rows · {len(t['columns'])} columns"} for t in table_summaries], "annotation": "Files are summarized side by side because no verified join was applied."}})
            measures = [t for t in table_summaries if "measure_total" in t]
            if measures:
                widgets.append({"id": "w_measures", "title": "Numeric totals by file", "type": "chart_line", "data": {"x_axis": [t["table"] for t in measures], "series": [t["measure_total"] for t in measures], "annotation": "Each total is computed independently; no join was used.", "sql": "; ".join(t["measure_sql"] for t in measures), "row_count": len(measures)}})
            scope_label = "All uploaded files"

        return {
            "id": f"dash_{uuid.uuid4().hex[:10]}", "title": title, "widget_count": len(widgets),
            "widgets": widgets, "scope": scope_table or "combined", "scope_label": scope_label,
            "relationships_used": [], "explanation": "Independent live summaries; tables are shown side by side unless a verified relationship is selected.",
        }
