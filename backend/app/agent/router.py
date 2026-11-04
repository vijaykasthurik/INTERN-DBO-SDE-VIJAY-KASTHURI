"""Intent Router classifying user queries into 8 specialized execution lanes."""

import re
from typing import Literal

from pydantic import BaseModel, Field

RouteLane = Literal[
    "quick_lookup",
    "analysis",
    "investigation",
    "anomaly",
    "forecast",
    "dashboard",
    "code_request",
    "clarify",
]


class RouteDecision(BaseModel):
    """Classification decision output produced by the intent router."""

    lane: RouteLane
    confidence: float
    reason: str
    clarification_question: str | None = None
    clarification_options: list[str] = Field(default_factory=list)


class IntentRouter:
    """Classifies natural language queries into one of the 8 specialized analytical lanes."""

    def route(self, question: str) -> RouteDecision:
        """Route user query using deterministic keyword parsing and heuristic intent mapping."""
        q = question.strip().lower()

        # 1. Ambiguous or underspecified queries -> clarify lane
        if q in ("sales", "revenue", "data", "analyze", "show", "help", "orders", "customers"):
            return RouteDecision(
                lane="clarify",
                confidence=0.99,
                reason="Query is ambiguous; requesting clarification.",
                clarification_question="What aspect of sales would you like to analyze?",
                clarification_options=[
                    "Highest revenue regions",
                    "Monthly sales trends",
                    "Underperforming products",
                    "Top 5 customers by spend",
                ],
            )

        # 2. Code generation requests
        if re.search(
            r"\b(generate\s+sql|show\s+sql|write\s+sql|sql\s+query|pandas\s+code|give\s+me\s+sql)\b",
            q,
        ):
            return RouteDecision(
                lane="code_request",
                confidence=0.98,
                reason="User explicitly requested SQL or Pandas code generation.",
            )

        # 3. Anomaly detection
        if any(
            w in q
            for w in (
                "anomaly",
                "anomalies",
                "outlier",
                "outliers",
                "unusual",
                "spike",
                "irregular",
            )
        ):
            return RouteDecision(
                lane="anomaly",
                confidence=0.96,
                reason="Anomaly or outlier detection intent detected.",
            )

        # 4. Forecasting & Predictive requests
        if any(
            w in q
            for w in ("forecast", "predict", "projection", "future", "next quarter", "next month")
        ):
            return RouteDecision(
                lane="forecast",
                confidence=0.95,
                reason="Time-series forecasting intent detected.",
            )

        # 5. Root-cause Investigation & Hypothesis testing
        if (
            q.startswith("why")
            or "why did" in q
            or "root cause" in q
            or "explain the drop" in q
            or "explain the dip" in q
            or "reason for" in q
        ):
            return RouteDecision(
                lane="investigation",
                confidence=0.94,
                reason="Root cause investigation / hypothesis testing intent detected.",
            )

        # 6. Dashboard requests
        if "dashboard" in q or "kpi overview" in q or "executive summary" in q:
            return RouteDecision(
                lane="dashboard",
                confidence=0.97,
                reason="Multi-widget dashboard compilation intent detected.",
            )

        # 7. Quick point lookups (single row or order lookup)
        if re.search(r"\border\s+[a-z0-9\-]+\b", q) or re.search(r"\bcustomer\s+[a-z0-9\-]+\b", q):
            return RouteDecision(
                lane="quick_lookup",
                confidence=0.92,
                reason="Single entity point lookup detected.",
            )

        # 8. Standard Analysis (aggregations, rankings, comparisons, trends)
        return RouteDecision(
            lane="analysis",
            confidence=0.90,
            reason="Standard analytical aggregation or comparison detected.",
        )
