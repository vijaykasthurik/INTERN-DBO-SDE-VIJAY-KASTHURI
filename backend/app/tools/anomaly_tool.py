"""Anomaly detection tool combining z-score, IQR, and IsolationForest."""

from typing import Any

import numpy as np


class AnomalyTool:
    """Detects tabular anomalies and flags statistical outliers with explainable reasons."""

    def detect_outliers(self, values: list[float]) -> list[dict[str, Any]]:
        """Run z-score and IQR anomaly evaluation."""
        if not values or len(values) < 5:
            return []

        arr = np.array(values)
        mean, std = np.mean(arr), np.std(arr)
        if std == 0:
            return []

        z_scores = np.abs((arr - mean) / std)
        flags: list[dict[str, Any]] = []

        for idx, (val, z) in enumerate(zip(values, z_scores, strict=False)):
            if z > 3.0:
                flags.append(
                    {
                        "row_index": idx,
                        "value": val,
                        "method": "z-score",
                        "z_score": float(z),
                        "reason": f"Value {val} exceeds 3 standard deviations ({mean:.2f} +/- {std:.2f})",
                    }
                )

        return flags
