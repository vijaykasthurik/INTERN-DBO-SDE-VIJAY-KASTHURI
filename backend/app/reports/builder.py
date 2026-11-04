"""Report builder assembling narrative, metrics, charts, and queries from the Evidence Ledger."""

from datetime import UTC, datetime
from typing import Any


class ReportBuilder:
    """Compiles structured reports from chat session evidence and analytical findings."""

    def build_report_data(
        self,
        session_id: str | None,
        messages: list[dict[str, Any]],
        title: str = "Lumen Executive Analytical Report",
        dataset_name: str = "Session analytical evidence",
        dashboard: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aggregate executive summary, queries, anomalies, and charts into printable report structure."""
        findings: list[dict[str, Any]] = []
        sql_queries: list[dict[str, Any]] = []
        anomalies_detected: list[dict[str, Any]] = []
        charts: list[dict[str, Any]] = []

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            evidence = msg.get("evidence", {}) or {}

            if role == "assistant":
                verification = evidence.get("verification", {})
                confidence = verification.get("confidence", msg.get("confidence", "Unknown"))
                verified = bool(verification) and confidence in {"High", "Medium"}
                # Extract SQL queries from evidence
                steps = evidence.get("entries", evidence.get("steps", []))
                for s in steps:
                    if s.get("tool") == "sql_tool" and s.get("code"):
                        sql_queries.append({
                            "query": s["code"],
                            "runtime_ms": s.get("runtime_ms"),
                            "row_count": s.get("row_count"),
                        })
                    if s.get("tool") == "overview_tool" and isinstance(s.get("result_preview"),dict):
                        for query in s["result_preview"].get("queries",[]):
                            sql_queries.append({"query":query,"runtime_ms":None,"row_count":None})
                    if s.get("tool") == "chart_tool" and s.get("result_preview"):
                        spec = s["result_preview"]
                        if "xAxis" in spec and spec.get("series"):
                            charts.append({"title":spec.get("title",{}).get("text","Recorded chart"),"data":{"x_axis":spec.get("xAxis",{}).get("data",[]),"series":spec["series"][0].get("data",[])}})
                        else:
                            charts.append(spec)

                # Check for anomaly mentions
                if "outlier" in content.lower() or "anomal" in content.lower():
                    anomalies_detected.append({
                        "finding": content,
                            "confidence": confidence,
                    })

                findings.append({
                    "summary": content[:240] + ("..." if len(content) > 240 else ""),
                    "full_text": content,
                    "confidence": confidence,
                    "verified": verified,
                })

        if dashboard:
            dataset_name = str(dashboard.get("scope_label") or "Selected datasets")
            for widget in dashboard.get("widgets", []):
                data = widget.get("data", {})
                findings.append({
                    "summary": str(widget.get("title", "Dashboard result")),
                    "full_text": str(data.get("annotation") or data.get("comparison") or data.get("primary_value") or widget.get("title", "Dashboard result")),
                    "confidence": "Medium",
                    "verified": False,
                })
                if data.get("sql"):
                    sql_queries.append({"query": data["sql"], "runtime_ms": data.get("runtime_ms"), "row_count": data.get("row_count")})
                if widget.get("type", "").startswith("chart"):
                    charts.append(widget)

        if not findings:
            raise ValueError("A report requires at least one real assistant result or dashboard widget.")

        return {
            "title": title,
            "session_id": session_id,
            "dataset_name": dataset_name,
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "executive_summary": findings[0]["full_text"],
            "data_health": None,
            "findings": findings,
            "sql_queries": sql_queries,
            "anomalies": anomalies_detected,
            "charts": charts,
            "verifier_audit": {
                "number_grounding": "See recorded verifier status for each finding.",
                "confidence_notes": [
                    {"confidence": finding["confidence"], "verified": finding["verified"]}
                    for finding in findings
                ],
            },
        }
