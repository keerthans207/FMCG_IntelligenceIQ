"""
Forecast evaluation metrics.

Computes MAE, RMSE, MAPE, and compares against a baseline.
Does not fabricate accuracy — reports honest metrics.
"""

from __future__ import annotations

import math
from typing import Any


def calculate_metrics(
    actual: list[float],
    predicted: list[float],
) -> dict[str, float]:
    """
    Calculate evaluation metrics for a set of predictions.

    Parameters
    ----------
    actual : list of actual values
    predicted : list of predicted values (same length)

    Returns
    -------
    dict with MAE, RMSE, MAPE (None if undefined)
    """
    if len(actual) != len(predicted):
        raise ValueError(f"Length mismatch: actual={len(actual)}, predicted={len(predicted)}")
    if len(actual) == 0:
        return {"mae": 0.0, "rmse": 0.0, "mape": None}

    n = len(actual)
    abs_errors = [abs(a - p) for a, p in zip(actual, predicted)]
    sq_errors = [(a - p) ** 2 for a, p in zip(actual, predicted)]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(sq_errors) / n)

    # MAPE: only where actual > 0 (undefined for zero actual)
    mape_values = [abs(a - p) / a * 100 for a, p in zip(actual, predicted) if a > 0]
    mape = sum(mape_values) / len(mape_values) if mape_values else None

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2) if mape is not None else None,
    }


def compare_to_baseline(
    actual: list[float],
    predicted: list[float],
    baseline_predicted: list[float],
) -> dict[str, Any]:
    """
    Compare ML model predictions against a simple baseline.

    The baseline uses the average of recent historical demand
    (or last observed value) as the prediction.

    Returns metrics for both and a comparison summary.
    """
    model_metrics = calculate_metrics(actual, predicted)
    baseline_metrics = calculate_metrics(actual, baseline_predicted)

    # Improvement over baseline (positive = model is better)
    mae_improvement = baseline_metrics["mae"] - model_metrics["mae"]
    rmse_improvement = baseline_metrics["rmse"] - model_metrics["rmse"]

    return {
        "model_metrics": model_metrics,
        "baseline_metrics": baseline_metrics,
        "mae_improvement": round(mae_improvement, 4),
        "rmse_improvement": round(rmse_improvement, 4),
        "model_better": mae_improvement > 0,
    }
