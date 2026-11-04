"""Evidence-only narrative composition for verified analytical execution results."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.agent.ledger import EvidenceLedger


class FinalNarrative(BaseModel):
    """Complete structured response package."""

    direct_answer: str
    business_insight: str
    how_i_got_this: str
    chart_spec: dict[str, Any] | None = None
    confidence: str = "High"
    suggested_followups: list[str] = Field(default_factory=list)
    sql_code: str | None = None
    pandas_code: str | None = None


class Narrator:
    """Compose output only from successful step code and the Evidence Ledger preview."""

    def compose_final(
        self,
        question: str,
        lane: str,
        ledger: EvidenceLedger,
        confidence: str = "High",
    ) -> FinalNarrative:
        sql_entries = [entry for entry in ledger.entries if entry.tool == "sql_tool" and entry.status == "success"]
        pandas_entries = [entry for entry in ledger.entries if entry.tool == "pandas_tool" and entry.status == "success"]
        chart_entry = next((entry for entry in ledger.entries if entry.tool == "chart_tool" and entry.status == "success" and isinstance(entry.result_preview, dict)), None)
        sql_code = sql_entries[-1].code if sql_entries else None
        pandas_code = pandas_entries[-1].code if pandas_entries else None

        if lane == "code_request":
            code_sections = []
            if sql_code:
                code_sections.append(f"**Executed DuckDB SQL:**\n```sql\n{sql_code}\n```")
            if pandas_code:
                code_sections.append(f"**Executed Pandas code:**\n```python\n{pandas_code}\n```")
            answer = "\n\n".join(code_sections) or "No code execution succeeded, so there is no verified code to return."
        else:
            summaries: list[str] = []
            for entry in sql_entries:
                rows = entry.result_preview
                if isinstance(rows, list):
                    if not rows:
                        summaries.append("The executed query returned no matching rows.")
                        continue
                    displayed_rows = rows[-8:] if any(isinstance(row, dict) and any(key.lower() in {"month", "period", "date"} for key in row) for row in rows) else rows[:8]
                    for row in displayed_rows:
                        if isinstance(row, dict):
                            values = ", ".join(f"{key}: {self._display(value)}" for key, value in row.items())
                            summaries.append(values)
                elif isinstance(rows, dict):
                    summaries.append(self._display(rows))
            for entry in ledger.entries:
                if entry.status == "success" and entry.tool in {"anomaly_tool", "forecast_tool", "hypothesis_tool", "dashboard_tool"}:
                    summaries.append(f"{entry.tool} result: {self._display(entry.result_preview)}")
            answer = "\n\n".join(summaries) or "No successful query result is available in the Evidence Ledger."

        evidence_methods = [entry.tool for entry in ledger.entries if entry.status == "success"]
        how = "; ".join(dict.fromkeys(evidence_methods))
        how_text = f"Computed from successful Evidence Ledger steps: {how}." if how else "No successful execution step was recorded."
        insight = "The result reflects the rows returned by the executed analytical query."
        if lane == "code_request":
            insight = "The code shown above is the code recorded for the successful execution step."
        if not sql_entries and not pandas_entries:
            confidence = "Low"

        return FinalNarrative(
            direct_answer=answer,
            business_insight=insight,
            how_i_got_this=how_text,
            chart_spec=chart_entry.result_preview if chart_entry else None,
            confidence=confidence,
            suggested_followups=["Break down this result by a column", "Compare results across time", "Inspect the executed query"],
            sql_code=sql_code,
            pandas_code=pandas_code,
        )

    @staticmethod
    def _display(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, float):
            return format(Decimal(str(value)), ",")
        if isinstance(value, int):
            return format(value, ",")
        return str(value)

    async def stream_tokens(self, text: str) -> AsyncGenerator[str, None]:
        """Stream the already-grounded final narrative in words."""
        for word in text.split(" "):
            yield word + " "
