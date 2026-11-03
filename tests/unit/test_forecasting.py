"""
Unit tests for forecast feature engineering and evaluation metrics.

Verifies data leakage prevention, lag features, rolling means, and
evaluation metric calculations.
"""

import pytest
from datetime import date, timedelta

from fmcg.forecasting.features import (
    build_feature_row,
    compute_lag_features,
    compute_rolling_mean,
)
from fmcg.forecasting.evaluation import calculate_metrics, compare_to_baseline


class TestLagFeatures:

    def test_lag_1_uses_previous_day(self):
        sales = [
            {"date": "2025-06-01", "units_sold": 10},
            {"date": "2025-06-02", "units_sold": 20},
            {"date": "2025-06-03", "units_sold": 30},
        ]
        result = compute_lag_features(sales, lag_days=[1])
        assert result[0]["lag_1"] == 0.0  # no history before first day
        assert result[1]["lag_1"] == 10.0  # previous day was 10
        assert result[2]["lag_1"] == 20.0  # previous day was 20

    def test_lag_7_uses_week_ago(self):
        sales = [
            {"date": (date(2025, 6, 1) + timedelta(days=i)).isoformat(), "units_sold": i + 1}
            for i in range(14)
        ]
        result = compute_lag_features(sales, lag_days=[7])
        # Day 8 (index 7) should have lag_7 = day 1's value = 1
        assert result[7]["lag_7"] == 1.0

    def test_no_leakage_from_future(self):
        """Lag features should never use future data."""
        sales = [
            {"date": "2025-06-01", "units_sold": 10},
            {"date": "2025-06-02", "units_sold": 20},
            {"date": "2025-06-03", "units_sold": 30},
        ]
        result = compute_lag_features(sales, lag_days=[1])
        # First day has no history → lag_1 should be 0, not 20 (next day)
        assert result[0]["lag_1"] == 0.0


class TestRollingMean:

    def test_rolling_mean_excludes_current(self):
        """Rolling mean should NOT include the current day (no leakage)."""
        sales = [
            {"date": "2025-06-01", "units_sold": 10},
            {"date": "2025-06-02", "units_sold": 20},
            {"date": "2025-06-03", "units_sold": 30},
        ]
        result = compute_rolling_mean(sales, window=2)
        # Day 3 (index 2): mean of days 1-2 = (10 + 20) / 2 = 15.0
        # Does NOT include day 3's own value (30)
        assert result[2]["rolling_mean_2"] == 15.0

    def test_empty_sales(self):
        result = compute_rolling_mean([], window=7)
        assert result == []

    def test_insufficient_window(self):
        """When fewer days than window, uses available history."""
        sales = [
            {"date": "2025-06-01", "units_sold": 10},
            {"date": "2025-06-02", "units_sold": 20},
        ]
        result = compute_rolling_mean(sales, window=7)
        # Day 2 (index 1): only 1 previous day available → mean = 10.0
        assert result[1]["rolling_mean_7"] == 10.0


class TestBuildFeatureRow:

    def test_feature_row_contains_all_expected_fields(self):
        historical = [
            {"date": (date(2025, 6, 1) + timedelta(days=i)).isoformat(),
             "units_sold": 10 + i}
            for i in range(20)
        ]
        target = date(2025, 6, 21)
        row = build_feature_row("SKU00001", "LOC0001", target, historical)

        assert row["sku_id"] == "SKU00001"
        assert row["location_id"] == "LOC0001"
        assert row["target_date"] == "2025-06-21"
        assert "day_of_week" in row
        assert "month" in row
        assert "is_weekend" in row
        assert "lag_1" in row
        assert "lag_7" in row
        assert "lag_14" in row
        assert "rolling_mean_7" in row
        assert "rolling_mean_14" in row
        assert "demand_trend" in row
        assert "promotion_flag" in row

    def test_no_future_data_in_features(self):
        """Feature row for June 21 should not use June 21+ data."""
        historical = [
            {"date": (date(2025, 6, 1) + timedelta(days=i)).isoformat(),
             "units_sold": 10}
            for i in range(20)
        ]
        target = date(2025, 6, 21)
        row = build_feature_row("SKU00001", "LOC0001", target, historical)

        # lag_1 should be June 20's value (10), not June 21's
        assert row["lag_1"] == 10.0
        # rolling_mean_7 should be mean of June 14-20 (all 10) = 10.0
        assert row["rolling_mean_7"] == 10.0


class TestEvaluationMetrics:

    def test_mae_calculation(self):
        actual = [10, 20, 30]
        predicted = [12, 18, 33]
        # errors: |10-12|=2, |20-18|=2, |30-33|=3 → MAE = 7/3 ≈ 2.333
        metrics = calculate_metrics(actual, predicted)
        assert abs(metrics["mae"] - 7/3) < 0.01

    def test_rmse_calculation(self):
        actual = [10, 20, 30]
        predicted = [10, 20, 30]
        metrics = calculate_metrics(actual, predicted)
        assert metrics["rmse"] == 0.0
        assert metrics["mae"] == 0.0

    def test_mape_with_zero_actual(self):
        """MAPE should be None when all actual values are zero."""
        actual = [0, 0, 0]
        predicted = [1, 2, 3]
        metrics = calculate_metrics(actual, predicted)
        assert metrics["mape"] is None

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            calculate_metrics([1, 2], [1])

    def test_empty_lists(self):
        metrics = calculate_metrics([], [])
        assert metrics["mae"] == 0.0


class TestCompareToBaseline:

    def test_model_better_than_baseline(self):
        actual = [10, 20, 30, 40]
        model_pred = [11, 19, 31, 39]   # close to actual
        baseline_pred = [25, 25, 25, 25]  # naive average
        result = compare_to_baseline(actual, model_pred, baseline_pred)
        assert result["model_better"] is True
        assert result["mae_improvement"] > 0

    def test_baseline_better_than_model(self):
        actual = [10, 20, 30, 40]
        model_pred = [50, 5, 60, 10]    # terrible
        baseline_pred = [25, 25, 25, 25]
        result = compare_to_baseline(actual, model_pred, baseline_pred)
        assert result["model_better"] is False
        assert result["mae_improvement"] < 0

    def test_equal_predictions(self):
        actual = [10, 20, 30]
        pred = [10, 20, 30]
        result = compare_to_baseline(actual, pred, pred)
        assert result["mae_improvement"] == 0.0
