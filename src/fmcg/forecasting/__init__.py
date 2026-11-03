"""Demand forecasting: feature engineering, baseline, evaluation."""
from fmcg.forecasting.features import build_feature_row, compute_lag_features, compute_rolling_mean
from fmcg.forecasting.evaluation import calculate_metrics, compare_to_baseline

__all__ = [
    "build_feature_row",
    "compute_lag_features",
    "compute_rolling_mean",
    "calculate_metrics",
    "compare_to_baseline",
]
