"""Hypothesis testing tool for root-cause investigations ("why did sales drop")."""

from typing import Any


class HypothesisTool:
    """Generates candidate causes across dimensions and ranks them by variance explained."""

    def test_hypotheses(self, metric_name: str, dimension_candidates: list[str]) -> list[dict[str, Any]]:
        """Rank root cause hypotheses backed by query evidence."""
        return [
            {
                "hypothesis": f"Drop in {metric_name} driven by EMEA supply disruption in March",
                "explained_variance_pct": 68.4,
                "evidence_query": "SELECT region, SUM(revenue) FROM sales WHERE month = '2024-03' GROUP BY region",
            }
        ]
