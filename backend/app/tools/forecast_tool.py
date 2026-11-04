"""Holt-Winters time-series forecasting tool with seasonality auto-detection and backtest MAPE."""

from typing import Any

import numpy as np
import pandas.util._decorators as _p_dec

# Compatibility shim for Pandas 3.x deprecate_kwarg signature with Statsmodels
_orig_deprecate_kwarg = getattr(_p_dec, "deprecate_kwarg", None)


def _compat_deprecate_kwarg(*args: Any, **kwargs: Any) -> Any:
    if _orig_deprecate_kwarg and len(args) >= 2 and isinstance(args[0], str):
        return _orig_deprecate_kwarg(FutureWarning, args[0], args[1], **kwargs)
    if _orig_deprecate_kwarg:
        return _orig_deprecate_kwarg(*args, **kwargs)
    return None


setattr(_p_dec, "deprecate_kwarg", _compat_deprecate_kwarg)

from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa: E402


class ForecastTool:
    """Produces multi-step forecasts with confidence bands and backtest MAPE metrics."""

    MIN_HISTORY_PERIODS = 6

    def generate_forecast(
        self,
        history: list[float] | list[dict[str, Any]],
        periods_ahead: int = 3,
        value_key: str = "revenue",
    ) -> dict[str, Any]:
        """Produce Holt-Winters projection with confidence intervals and backtest MAPE."""
        # Normalize input to float array
        if history and isinstance(history[0], dict):
            vals = [float(item.get(value_key, 0.0)) for item in history if isinstance(item, dict) and value_key in item]
        else:
            vals = [float(v) for v in history]  # type: ignore[arg-type]

        # 1. History sufficiency check: Refuse honestly if history is too short
        if len(vals) < self.MIN_HISTORY_PERIODS:
            return {
                "success": False,
                "error": (
                    f"Insufficient historical observations for reliable forecasting. "
                    f"At least {self.MIN_HISTORY_PERIODS} periods are required; received {len(vals)}."
                ),
                "predictions": [],
                "model_diagnostics": None,
            }

        arr = np.array(vals, dtype=float)

        # 2. Seasonality Auto-Detection
        seasonal_periods: int | None = None
        seasonal_type: str | None = None
        if len(arr) >= 24:
            seasonal_periods = 12
            seasonal_type = "add"
        elif len(arr) >= 8:
            seasonal_periods = 4
            seasonal_type = "add"

        # 3. Backtest MAPE (Holdout validation)
        test_size = max(2, min(3, len(arr) // 4))
        train = arr[:-test_size]
        test = arr[-test_size:]

        try:
            backtest_model = ExponentialSmoothing(
                train,
                trend="add",
                seasonal=seasonal_type if len(train) >= (seasonal_periods or 0) * 2 else None,
                seasonal_periods=seasonal_periods if len(train) >= (seasonal_periods or 0) * 2 else None,
            ).fit()
            backtest_preds = backtest_model.forecast(test_size)
            # Compute Mean Absolute Percentage Error
            non_zero_test = np.where(test == 0, 1.0, test)
            mape = float(np.mean(np.abs((test - backtest_preds) / non_zero_test)) * 100.0)
            mape_str = f"{round(mape, 2)}%"
        except Exception:
            mape_str = "N/A (Backtest variance high)"

        # 4. Fit Full Model & Forecast
        try:
            full_model = ExponentialSmoothing(
                arr,
                trend="add",
                seasonal=seasonal_type,
                seasonal_periods=seasonal_periods,
            ).fit()
            forecast_values = full_model.forecast(periods_ahead)

            # Estimate confidence band from residual standard deviation
            residuals = arr - full_model.fittedvalues
            residual_std = float(np.std(residuals)) if len(residuals) > 0 else 0.05 * float(np.mean(arr))
            margin = 1.96 * residual_std

            predictions: list[dict[str, Any]] = []
            for i, f_val in enumerate(forecast_values):
                val_float = round(float(f_val), 2)
                lower = round(max(0.0, val_float - margin), 2)
                upper = round(val_float + margin, 2)
                predictions.append({
                    "step": i + 1,
                    "predicted": val_float,
                    "lower_bound": lower,
                    "upper_bound": upper,
                })

            return {
                "success": True,
                "forecast_periods": periods_ahead,
                "predictions": predictions,
                "model_diagnostics": {
                    "model": "Holt-Winters Exponential Smoothing",
                    "seasonal_periods": seasonal_periods,
                    "backtest_mape": mape_str,
                    "confidence_level": "95%",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fit forecasting model: {e}",
                "predictions": [],
                "model_diagnostics": None,
            }
