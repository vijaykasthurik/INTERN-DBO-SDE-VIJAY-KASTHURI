"""Evidence-based revenue-change decomposition; does not infer external causes."""
from typing import Any

import pandas as pd


class HypothesisTool:
    def investigate_drop(self, df: pd.DataFrame | None = None, target_period: str | None = None, target_region: str | None = None) -> dict[str, Any]:
        if df is None or df.empty:
            raise ValueError("Investigation requires live source rows.")
        required = {"order_date","quantity","unit_price","discount"}
        if not required.issubset(df.columns):
            raise ValueError("Revenue decomposition requires order_date, quantity, unit_price and discount columns.")
        frame = df.copy()
        frame["period"] = pd.to_datetime(frame["order_date"],errors="coerce").dt.to_period("M").astype(str)
        periods = sorted(value for value in frame["period"].unique() if value != "NaT")
        period = target_period or (periods[-1] if periods else None)
        if period not in periods or periods.index(period) == 0:
            raise ValueError("Investigation needs a target month and an earlier comparison month in the data.")
        period = str(period)
        baseline = str(periods[periods.index(period)-1])
        if target_region and "region" not in frame:
            raise ValueError("No region column is available for the requested regional investigation.")
        if target_region:
            frame = frame[frame["region"] == target_region]
        frame = frame.dropna(subset=list(required))
        frame["gross"] = frame["quantity"] * frame["unit_price"]
        frame["net"] = frame["gross"] * (1-frame["discount"])

        def metrics(month: str) -> dict[str, float]:
            subset = frame[frame["period"] == month]
            if subset.empty:
                raise ValueError("No comparable rows exist for both requested periods and region.")
            quantity = float(subset["quantity"].sum())
            gross = float(subset["gross"].sum())
            net = float(subset["net"].sum())
            if quantity == 0 or gross == 0:
                raise ValueError("Cannot decompose revenue with a zero quantity or gross baseline.")
            return {"quantity":quantity,"gross_unit_price":gross/quantity,"effective_discount":1-net/gross,"revenue":net,"orders":float(len(subset))}

        before,after = metrics(baseline),metrics(period)
        change = after["revenue"]-before["revenue"]
        volume = (after["quantity"]-before["quantity"])*before["gross_unit_price"]*(1-before["effective_discount"])
        price = after["quantity"]*(after["gross_unit_price"]-before["gross_unit_price"])*(1-before["effective_discount"])
        discount = -after["quantity"]*after["gross_unit_price"]*(after["effective_discount"]-before["effective_discount"])
        contributions = [("volume",volume),("unit_price",price),("discount",discount)]
        ranked: list[dict[str, Any]] = [{"dimension":dimension,"hypothesis":f"Observed {dimension} contribution in {target_region or 'the selected data'}", "revenue_effect":effect,"explained_variance_ratio":abs(effect)/abs(change) if change else 0.0,"status":"supported" if effect < 0 and change < 0 else "not_supported", "evidence":{"baseline":before,"current":after}} for dimension,effect in contributions]
        ranked.append({"dimension":"interaction_residual","hypothesis":"Unexplained decomposition residual", "revenue_effect":change-volume-price-discount,"explained_variance_ratio":abs(change-volume-price-discount)/abs(change) if change else 0.0,"status":"not_supported","evidence":{"revenue_change":change}})
        ranked.sort(key=lambda candidate: abs(candidate["revenue_effect"]),reverse=True)
        for index,candidate in enumerate(ranked,1):
            candidate["rank"] = index
        return {"target_period":period,"baseline_period":baseline,"target_region":target_region,"primary_cause":ranked[0]["hypothesis"],"ranked_hypotheses":ranked,"revenue_change":change,"limitation":"This is an accounting decomposition of observed changes. The dataset does not establish external causal explanations such as supply disruption.","summary":{"hypotheses_evaluated":len(ranked),"supported_count":sum(candidate["status"]=="supported" for candidate in ranked),"top_explained_variance":ranked[0]["explained_variance_ratio"]}}
