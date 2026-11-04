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
        scope_tables: list[str] | None = None,
        source_names: dict[str,str] | None = None,
    ) -> dict[str, Any]:
        if not db_path or not os.path.exists(db_path):
            raise ValueError("Upload a dataset before generating a dashboard.")
        con = duckdb.connect(db_path, read_only=True)
        try:
            tables = [str(row[0]) for row in con.execute("SHOW TABLES").fetchall()]
            if scope_tables is not None:
                tables = [table for table in tables if table in scope_tables]
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
                count_result = con.execute(f'SELECT COUNT(*) AS row_count FROM "{table}"').fetchone()
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
                    value_result = con.execute(f'SELECT {aggregate} AS total FROM "{table}"').fetchone()
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

        source_count = len({(source_names or {}).get(table,table) for table in tables})
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
            if "measure_total" in item:
                widgets = [widget for widget in widgets if widget["id"] != "w_rows"]
                for widget in widgets:
                    if widget["id"] == "w_total":
                        widget["data"]["comparison"] = f"{item['row_count']:,} rows; {len(item['columns'])} columns"
            from app.data.quality import QualityAuditor
            from app.tools.anomaly_tool import AnomalyTool
            quality = QualityAuditor().evaluate_table_quality(db_path, item["table"])
            widgets = [widget for widget in widgets if widget["id"] != "w_schema"]
            widgets.append({"id":"w_quality", "title":"Data quality", "type":"alert_panel", "data":{"alerts_count":len(quality["issues"]), "items":[{"id":str(index),"severity":issue["severity"],"detail":issue["description"]} for index,issue in enumerate(quality["issues"])], "annotation":quality["summary"], "sql":"\n".join(quality["sql_queries"])}})
            con = duckdb.connect(db_path, read_only=True)
            try:
                if item["numeric"]:
                    target = next((column for column in item["numeric"] if column in {"revenue","unit_price","amount","price"}), item["numeric"][0])
                    sample_sql = f'SELECT * FROM "{item["table"]}" LIMIT 50000'
                    sample = con.execute(sample_sql).df()
                    anomalies = AnomalyTool().detect_anomalies(sample,target_column=target,id_column=sample.columns[0])
                    widgets.append({"id":"w_anomaly", "title":f"Unusual {target} values", "type":"alert_panel", "data":{"alerts_count":len(anomalies["outliers"]), "items":[{"id":row["id"],"severity":"warning","detail":row["reason"]} for row in anomalies["outliers"][:20]], "annotation":f"Statistical scan of {len(sample):,} rows; capped at 50,000. Flags are unusual values, not proven errors.", "sql":sample_sql}})
                    distribution_sql = f'SELECT CAST("{target}" AS VARCHAR) AS value, COUNT(*) AS frequency FROM "{item["table"]}" WHERE "{target}" IS NOT NULL GROUP BY "{target}" ORDER BY frequency DESC LIMIT 20'
                    distribution = con.execute(distribution_sql).fetchall()
                    widgets.append({"id":"w_distribution", "title":f"Most frequent {target} values", "type":"chart_line", "data":{"x_axis":[str(row[0]) for row in distribution],"series":[row[1] for row in distribution], "sql":distribution_sql, "annotation":"Frequency distribution of the most common observed values."}})
                if item.get("measure_sql") and item["categories"]:
                    category = next((column for column in item["categories"] if not column.lower().endswith("_id")), item["categories"][0])
                    aggregate = item["measure_sql"].split(" AS total FROM ")[0].removeprefix("SELECT ")
                    top_sql = f'SELECT CAST("{category}" AS VARCHAR), {aggregate} AS value FROM "{item["table"]}" GROUP BY "{category}" ORDER BY value DESC LIMIT 10'
                    top = con.execute(top_sql).fetchall()
                    widgets.append({"id":"w_top", "title":f"Top {category}", "type":"chart_pie", "data":{"slices":[{"name":str(row[0]),"value":float(row[1] or 0)} for row in top], "sql":top_sql, "annotation":"Top categories by the computed measure."}})
            finally:
                con.close()
            scope_label = item["table"]
        else:
            widgets.append({"id": "w_tables", "title": "Files analyzed", "type": "kpi_card", "data": {"primary_value": f"{source_count} files", "numeric_val": source_count, "comparison": "Live summaries from each uploaded file", "row_count": 1, "sql": "SHOW TABLES"}})
            widgets.append({"id": "w_rows", "title": "Rows by table", "type": "chart_pie", "data": {"slices": [{"name": t["table"], "value": t["row_count"]} for t in table_summaries], "sql": ";\n".join(f'SELECT COUNT(*) AS row_count FROM "{t["table"]}"' for t in table_summaries), "row_count": len(table_summaries)}})
            widgets.append({"id": "w_summary", "title": "Side-by-side file summaries", "type": "alert_panel", "data": {"alerts_count": 0, "items": [{"id": t["table"], "severity": "info", "detail": f"{t['row_count']:,} rows · {len(t['columns'])} columns"} for t in table_summaries], "sql": ";\n".join(f'DESCRIBE "{t["table"]}"; SELECT COUNT(*) AS row_count FROM "{t["table"]}"' for t in table_summaries), "annotation": "Files are summarized side by side because no verified join was applied."}})
            measures = [t for t in table_summaries if "measure_total" in t]
            if measures:
                widgets.append({"id": "w_measures", "title": "Numeric totals by file", "type": "chart_line", "data": {"x_axis": [t["table"] for t in measures], "series": [t["measure_total"] for t in measures], "annotation": "Each total is computed independently; no join was used.", "sql": "; ".join(t["measure_sql"] for t in measures), "row_count": len(measures)}})
            scope_label = "All uploaded files"

        relationships_used: list[str] = []
        if not scope_table and len(tables) > 1:
            from app.data.relationships import RelationshipDetector
            graph = RelationshipDetector().detect_table_relationships(db_path, tables)
            con = duckdb.connect(db_path, read_only=True)
            try:
                summaries = {item["table"]: item for item in table_summaries}
                for edge in graph:
                    if edge["confidence"] < 0.95:
                        continue
                    for fact, fk, dim, dk in [(edge["from_table"], edge["from_column"], edge["to_table"], edge["to_column"]), (edge["to_table"], edge["to_column"], edge["from_table"], edge["from_column"])]:
                        source = summaries[fact]
                        if "measure_sql" not in source:
                            continue
                        unique = con.execute(f'SELECT COUNT(*) = COUNT(DISTINCT "{dk}") FROM "{dim}"').fetchone()
                        if not unique or not unique[0]:
                            continue
                        join = f'FROM "{fact}" f LEFT JOIN "{dim}" d ON f."{fk}" = d."{dk}"'
                        counts = con.execute(f'SELECT COUNT(*), COUNT(d."{dk}") {join}').fetchone()
                        if not counts or counts[0] != source["row_count"] or counts[1] < source["row_count"] * 0.95:
                            continue
                        categories = [c for c in summaries[dim]["categories"] if c != dk and not c.endswith("_id")]
                        join_category = next((c for c in categories if c in {"segment", "category"}), categories[0] if categories else None)
                        if join_category is None:
                            continue
                        aggregate = source["measure_sql"].split(" AS total FROM ")[0].removeprefix("SELECT ")
                        for column in source["columns"]:
                            aggregate = aggregate.replace(f'"{column}"', f'f."{column}"')
                        sql = f'SELECT d."{join_category}" AS category, {aggregate} AS value {join} GROUP BY d."{join_category}" ORDER BY value DESC'
                        rows = con.execute(sql).fetchall()
                        label = f"{fact}.{fk} -> {dim}.{dk}"
                        relationships_used.append(label)
                        widgets.append({"id": f"join_{len(relationships_used)}", "title": f"{source['measure']} by {dim} {join_category}", "type": "chart_pie", "data": {"slices": [{"name": str(r[0]), "value": float(r[1] or 0)} for r in rows], "sql": sql, "row_count": len(rows), "annotation": f"Verified join: {counts[0]} joined rows match source rows.", "join_fanout_check": {"passed": True, "source_rows": source["row_count"], "joined_rows": counts[0]}}})
            finally:
                con.close()

        if relationships_used:
            for widget in widgets:
                if widget["id"] == "w_summary":
                    widget["data"]["annotation"] = "Independent file summaries; cross-file widgets below use validated joins."

        return {
            "id": f"dash_{uuid.uuid4().hex[:10]}", "title": title, "widget_count": len(widgets),
            "widgets": widgets, "scope": scope_table or "combined", "scope_label": scope_label,
            "relationships_used": relationships_used, "explanation": "Verified joins passed uniqueness, overlap and row-count checks." if relationships_used else "Side-by-side summaries: no reliable join passed validation.",
        }
