"""Anomaly detection tool combining z-score, IQR, and IsolationForest ensemble."""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyTool:
    """Detects tabular anomalies and flags statistical outliers with explainable reasons."""

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        target_column: str = "unit_price",
        id_column: str = "order_id",
    ) -> dict[str, Any]:
        """Execute ensemble anomaly detection using Z-score, IQR fencing, and Isolation Forest."""
        if df.empty or target_column not in df.columns:
            return {"outliers": [], "duplicates": [], "summary": {"outliers_detected": 0, "duplicate_rows": 0}}

        series = pd.to_numeric(df[target_column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) < 10:
            return {"outliers": [], "duplicates": [], "summary": {"outliers_detected": 0, "duplicate_rows": 0}}

        vals: np.ndarray = np.asarray(series.to_numpy(), dtype=float)
        mean = float(np.mean(vals))
        std = float(np.std(vals))
        q1 = float(np.percentile(vals, 25))
        median = float(np.median(vals))
        q3 = float(np.percentile(vals, 75))
        iqr = q3 - q1
        upper_iqr = q3 + 1.5 * iqr

        # 1. Z-Score flags
        z_scores = np.abs((vals - mean) / (std if std > 0 else 1.0))
        z_flagged_indices = set(np.where(z_scores > 3.0)[0])

        # 2. IQR flags
        iqr_flagged_indices = set(np.where(vals > upper_iqr)[0])

        # 3. Isolation Forest flags
        iso = IsolationForest(contamination=0.005, random_state=42)
        iso_preds = iso.fit_predict(vals.reshape(-1, 1))
        iso_flagged_indices = set(np.where(iso_preds == -1)[0])

        # Combine ensemble: flag if at least 2 methods agree, or z > 4.0
        outliers: list[dict[str, Any]] = []
        for i, val in enumerate(vals):
            methods_fired = []
            if i in z_flagged_indices:
                methods_fired.append("z-score")
            if i in iqr_flagged_indices:
                methods_fired.append("iqr")
            if i in iso_flagged_indices:
                methods_fired.append("isolation_forest")

            if len(methods_fired) >= 2 or (i in z_flagged_indices and z_scores[i] > 4.0):
                row_idx = series.index[i]
                row_id = str(df.loc[row_idx, id_column]) if id_column in df.columns else f"row_{row_idx}"
                peer_ratio = round(val / (median if median > 0 else 1.0), 1)

                outliers.append({
                    "id": row_id,
                    "target_column": target_column,
                    "value": round(float(val), 2),
                    "methods_fired": methods_fired,
                    "z_score": round(float(z_scores[i]), 2),
                    "typical_range": {
                        "q1": round(q1, 2),
                        "median": round(median, 2),
                        "q3": round(q3, 2),
                        "upper_bound": round(upper_iqr, 2),
                    },
                    "peer_group_comparison": f"Value is {peer_ratio}x the dataset median ({median:.2f})",
                    "reason": f"Value {val:,.2f} exceeds typical range ({q1:.2f} - {upper_iqr:.2f}) and triggered: {', '.join(methods_fired)}",
                })

        # 4. Duplicate Block Detection
        duplicate_cols = [c for c in ["customer_id", "product_id", "order_date", "quantity", "unit_price"] if c in df.columns]
        duplicates: list[dict[str, Any]] = []
        if duplicate_cols:
            dupe_mask = df.duplicated(subset=duplicate_cols, keep="first")
            dupe_rows = df[dupe_mask]
            for _, r in dupe_rows.iterrows():
                duplicates.append({
                    "id": str(r.get(id_column, "dupe_row")),
                    "duplicate_fields": {col: r[col] for col in duplicate_cols},
                    "reason": "Exact duplicated record detected matching an earlier order transaction block.",
                })

        return {
            "outliers": sorted(outliers, key=lambda x: x["value"], reverse=True),
            "duplicates": duplicates,
            "summary": {
                "outliers_detected": len(outliers),
                "duplicate_rows": len(duplicates),
                "methods_used": ["z-score", "iqr", "isolation_forest"],
            },
        }
