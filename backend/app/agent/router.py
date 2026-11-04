"""Intent Router for question classification across 8 specialist lanes."""

from typing import Literal

from pydantic import BaseModel

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
    """Classification outcome produced by the intent router."""

    lane: RouteLane
    confidence: float
    reason: str


class IntentRouter:
    """Classifies user natural-language queries into execution lanes."""

    def route(self, question: str) -> RouteDecision:
        """Heuristic and fast-model classifier for question intent."""
        q = question.lower()
        if "sql" in q or "pandas" in q or "code" in q:
            return RouteDecision(lane="code_request", confidence=0.95, reason="User requested code")
        if "anomaly" in q or "outlier" in q:
            return RouteDecision(lane="anomaly", confidence=0.95, reason="Anomaly query")
        if "forecast" in q or "predict" in q or "future" in q:
            return RouteDecision(lane="forecast", confidence=0.90, reason="Forecasting query")
        if "why" in q and ("drop" in q or "dip" in q or "fall" in q):
            return RouteDecision(
                lane="investigation", confidence=0.90, reason="Hypothesis root-cause"
            )
        if "dashboard" in q:
            return RouteDecision(lane="dashboard", confidence=0.95, reason="Dashboard request")
        return RouteDecision(lane="analysis", confidence=0.85, reason="General analytical query")
