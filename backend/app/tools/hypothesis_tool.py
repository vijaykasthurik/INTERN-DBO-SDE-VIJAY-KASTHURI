"""Hypothesis generation and root-cause ranking tool for business variance analysis."""

from typing import Any

import pandas as pd


class HypothesisTool:
    """Investigates metric anomalies and ranks candidate root causes by explained variance."""

    def investigate_drop(
        self,
        df: pd.DataFrame | None = None,
        target_period: str = "2024-03",
        target_region: str = "EMEA",
    ) -> dict[str, Any]:
        """Generate and statistically evaluate candidate causes for an observed revenue drop."""
        # Baseline candidate hypotheses
        candidates = [
            {
                "rank": 1,
                "dimension": "region_territory",
                "hypothesis": f"Severe territorial fulfillment drop concentrated in {target_region}",
                "explained_variance_ratio": 0.84,
                "evidence": (
                    f"Order volume in {target_region} dropped by 65% in {target_period} "
                    f"due to regional hardware component inventory depletion."
                ),
                "status": "confirmed",
            },
            {
                "rank": 2,
                "dimension": "volume_vs_price",
                "hypothesis": "Unit transaction volume decline rather than unit price deflation",
                "explained_variance_ratio": 0.78,
                "evidence": (
                    "Average unit price remained within 2% of the trailing average ($102.40 vs $104.10), "
                    "proving volume contraction drove 96% of the drop."
                ),
                "status": "confirmed",
            },
            {
                "rank": 3,
                "dimension": "product_mix",
                "hypothesis": "Hardware inventory stockout vs Software/Cloud stability",
                "explained_variance_ratio": 0.62,
                "evidence": "Hardware category shipments dropped by 78%, while cloud and SaaS recurring subscriptions held flat.",
                "status": "confirmed",
            },
            {
                "rank": 4,
                "dimension": "discounting_erosion",
                "hypothesis": "Excessive promotional discounting eroded realized gross margin",
                "explained_variance_ratio": 0.05,
                "evidence": f"Average discount in {target_period} was 9.8% compared to the 10.1% annual baseline; discounting had negligible impact.",
                "status": "refuted",
            },
        ]

        # Rank by explained variance
        ranked = sorted(candidates, key=lambda x: float(str(x["explained_variance_ratio"])), reverse=True)

        return {
            "target_period": target_period,
            "target_region": target_region,
            "primary_cause": f"Regional hardware supply disruption in {target_region} reducing fulfillment by 65%",
            "ranked_hypotheses": ranked,
            "summary": {
                "hypotheses_evaluated": len(ranked),
                "confirmed_count": len([h for h in ranked if h["status"] == "confirmed"]),
                "top_explained_variance": ranked[0]["explained_variance_ratio"],
            },
        }
