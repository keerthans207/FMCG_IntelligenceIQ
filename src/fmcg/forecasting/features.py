"""
Forecast feature engineering.

Implements lag features, rolling averages, and temporal features
for demand forecasting. Pure Python for unit testing; the Spark job
applies the same logic at scale using window functions.

Critical: prevents data leakage by only using past data to generate
features for a given prediction point.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def compute_lag_features(
    daily_sales: list[dict[str, Any]],
    lag_days: list[int],
    date_field: str = "date",
    value_field: str = "units_sold",
) -> list[dict[str, Any]]:
    """
    Compute lag features for a sorted list of daily sales records.

    For each record, adds fields like 'lag_1', 'lag_7' containing the
    demand from N days prior. Only uses past data (no future leakage).

    daily_sales must be sorted by date ascending.
    """
    if not daily_sales:
        return []

    # Build a date -> value lookup
    date_to_value: dict[str, float] = {}
    for record in daily_sales:
        d = record[date_field]
        if isinstance(d, date):
            d = d.isoformat()
        date_to_value[d] = record[value_field]

    result: list[dict[str, Any]] = []
    for record in daily_sales:
        enriched = dict(record)
        current_date_str = record[date_field]
        if isinstance(current_date_str, date):
            current_date_str = current_date_str.isoformat()

        current_date = date.fromisoformat(current_date_str)

        for lag in lag_days:
            lag_date = current_date - timedelta(days=lag)
            lag_key = lag_date.isoformat()
            enriched[f"lag_{lag}"] = date_to_value.get(lag_key, 0.0)

        result.append(enriched)

    return result


def compute_rolling_mean(
    daily_sales: list[dict[str, Any]],
    window: int,
    date_field: str = "date",
    value_field: str = "units_sold",
) -> list[dict[str, Any]]:
    """
    Compute rolling mean of demand over a trailing window.

    For each record, adds 'rolling_mean_{window}' containing the mean
    of the previous N days of demand (NOT including the current day,
    to avoid leakage).

    daily_sales must be sorted by date ascending.
    """
    if not daily_sales:
        return []

    values = [record[value_field] for record in daily_sales]
    result: list[dict[str, Any]] = []

    for i, record in enumerate(daily_sales):
        enriched = dict(record)

        # Rolling window: look back at the previous `window` records
        # (not including current, to avoid leakage)
        start = max(0, i - window)
        window_values = values[start:i]

        if window_values:
            enriched[f"rolling_mean_{window}"] = round(sum(window_values) / len(window_values), 2)
        else:
            enriched[f"rolling_mean_{window}"] = 0.0

        result.append(enriched)

    return result


def build_feature_row(
    sku_id: str,
    location_id: str,
    target_date: date,
    historical_sales: list[dict[str, Any]],
    promotion_flag: bool = False,
) -> dict[str, Any]:
    """
    Build a single feature row for forecasting demand on `target_date`.

    Features:
        sku_id, location_id, day_of_week, month, is_weekend,
        lag_1, lag_7, lag_14, rolling_mean_7, rolling_mean_14,
        promotion_flag

    Uses only data from before target_date (no leakage).

    historical_sales: list of {date, units_sold} for this SKU/location,
                      sorted ascending by date, all before target_date.
    """
    # Temporal features
    dow = target_date.weekday()  # 0=Monday, 6=Sunday
    month = target_date.month
    is_weekend = dow >= 5

    # Lag features (demand from N days ago)
    date_to_sales: dict[str, float] = {}
    for record in historical_sales:
        d = record.get("date")
        if isinstance(d, date):
            d = d.isoformat()
        date_to_sales[d] = record.get("units_sold", 0)

    lag_1 = date_to_sales.get((target_date - timedelta(days=1)).isoformat(), 0.0)
    lag_7 = date_to_sales.get((target_date - timedelta(days=7)).isoformat(), 0.0)
    lag_14 = date_to_sales.get((target_date - timedelta(days=14)).isoformat(), 0.0)

    # Rolling means (trailing, excluding current day)
    recent_7 = [
        date_to_sales.get((target_date - timedelta(days=i)).isoformat(), 0.0)
        for i in range(1, 8)
    ]
    rolling_7 = round(sum(recent_7) / 7, 2)

    recent_14 = [
        date_to_sales.get((target_date - timedelta(days=i)).isoformat(), 0.0)
        for i in range(1, 15)
    ]
    rolling_14 = round(sum(recent_14) / 14, 2)

    # Recent trend (ratio of last 7 days to previous 7 days)
    previous_7 = [
        date_to_sales.get((target_date - timedelta(days=i)).isoformat(), 0.0)
        for i in range(8, 15)
    ]
    if sum(previous_7) > 0:
        trend = round(sum(recent_7) / sum(previous_7), 3)
    else:
        trend = 1.0

    return {
        "sku_id": sku_id,
        "location_id": location_id,
        "target_date": target_date.isoformat(),
        "day_of_week": dow,
        "month": month,
        "is_weekend": is_weekend,
        "lag_1": lag_1,
        "lag_7": lag_7,
        "lag_14": lag_14,
        "rolling_mean_7": rolling_7,
        "rolling_mean_14": rolling_14,
        "demand_trend": trend,
        "promotion_flag": promotion_flag,
    }
