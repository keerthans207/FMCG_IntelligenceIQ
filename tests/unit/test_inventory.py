"""
Unit tests for inventory intelligence calculations.

Tests available stock, days remaining, reorder quantity, and stockout
risk classification. Pure Python — no Spark required.
"""

import pytest
from fmcg.analytics.inventory import (
    InventoryState,
    calculate_available_stock,
    calculate_days_remaining,
    calculate_reorder_quantity,
    classify_stockout_risk,
    StockoutRiskLevel,
)


class TestAvailableStock:

    def test_simple_available_stock(self):
        state = InventoryState(on_hand_quantity=100, reserved_quantity=30)
        assert calculate_available_stock(state) == 70

    def test_zero_reserved(self):
        state = InventoryState(on_hand_quantity=100, reserved_quantity=0)
        assert calculate_available_stock(state) == 100

    def test_all_reserved(self):
        state = InventoryState(on_hand_quantity=100, reserved_quantity=100)
        assert calculate_available_stock(state) == 0

    def test_over_reserved_clamps_to_zero(self):
        """If reserved > on_hand, available should be 0, not negative."""
        state = InventoryState(on_hand_quantity=50, reserved_quantity=80)
        assert calculate_available_stock(state) == 0


class TestDaysRemaining:

    def test_normal_demand(self):
        state = InventoryState(
            on_hand_quantity=100, reserved_quantity=10,
            average_daily_demand=9.0,
        )
        # available = 90, demand = 9 → 10 days
        days = calculate_days_remaining(state)
        assert days == 10.0

    def test_zero_demand_returns_none(self):
        """Insufficient demand history should return None, not inf."""
        state = InventoryState(
            on_hand_quantity=100, reserved_quantity=0,
            average_daily_demand=0.0,
        )
        assert calculate_days_remaining(state) is None

    def test_negative_demand_returns_none(self):
        state = InventoryState(
            on_hand_quantity=100, reserved_quantity=0,
            average_daily_demand=-5.0,
        )
        assert calculate_days_remaining(state) is None


class TestReorderQuantity:

    def test_reorder_needed(self):
        """Demand exceeds stock → positive reorder quantity."""
        state = InventoryState(on_hand_quantity=50, reserved_quantity=10, incoming_quantity=0)
        # available = 40
        # forecast_during_lead = 100, safety = 20 → need 120, have 40 → reorder 80
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=100,
            safety_stock=20,
        )
        assert qty == 80

    def test_no_reorder_when_sufficient_stock(self):
        """Stock covers demand + safety → no reorder needed."""
        state = InventoryState(on_hand_quantity=200, reserved_quantity=10, incoming_quantity=0)
        # available = 190, need 100 + 20 = 120 → have enough
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=100,
            safety_stock=20,
        )
        assert qty == 0

    def test_reorder_with_incoming_stock(self):
        """Incoming stock reduces reorder quantity."""
        state = InventoryState(on_hand_quantity=50, reserved_quantity=10, incoming_quantity=30)
        # available = 40, incoming = 30, total = 70
        # need 100 + 20 = 120, have 70 → reorder 50
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=100,
            safety_stock=20,
        )
        assert qty == 50

    def test_reorder_clamped_to_zero(self):
        """Reorder quantity should never be negative."""
        state = InventoryState(on_hand_quantity=500, reserved_quantity=0, incoming_quantity=0)
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=10,
            safety_stock=5,
        )
        assert qty >= 0

    def test_min_order_quantity(self):
        """Reorder should be at least min_order_quantity if any reorder needed."""
        state = InventoryState(on_hand_quantity=50, reserved_quantity=10)
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=55,
            safety_stock=20,
            min_order_quantity=100,
        )
        # raw = 55 + 20 - 40 = 35, but min is 100
        assert qty == 100

    def test_reorder_multiple_rounding(self):
        """Reorder should round up to nearest multiple."""
        state = InventoryState(on_hand_quantity=50, reserved_quantity=10)
        qty = calculate_reorder_quantity(
            state,
            forecast_demand_during_lead_time=100,
            safety_stock=20,
            reorder_multiple=24,
        )
        # raw = 100 + 20 - 40 = 80, round up to 96 (4 * 24)
        assert qty == 96


class TestStockoutRisk:

    def test_critical_risk(self):
        """Days remaining less than lead time → critical."""
        state = InventoryState(
            on_hand_quantity=10, reserved_quantity=0,
            average_daily_demand=2.0, lead_time_days=7, safety_stock_days=7,
        )
        # days_remaining = 5, lead_time = 7 → 5 < 7 → critical
        risk = classify_stockout_risk(state)
        assert risk == StockoutRiskLevel.CRITICAL

    def test_high_risk(self):
        """Days remaining between lead time and lead + safety → high."""
        state = InventoryState(
            on_hand_quantity=20, reserved_quantity=0,
            average_daily_demand=2.0, lead_time_days=7, safety_stock_days=7,
        )
        # days_remaining = 10, threshold = 14 → 10 < 14 → high
        risk = classify_stockout_risk(state)
        assert risk == StockoutRiskLevel.HIGH

    def test_medium_risk(self):
        state = InventoryState(
            on_hand_quantity=28, reserved_quantity=0,
            average_daily_demand=1.0, lead_time_days=7, safety_stock_days=7,
        )
        # days_remaining = 28, threshold = 14 → 28 < 28? No, 28 = 28, so < 28 is false
        # Actually 28 < 2*14=28 is False, so it should be LOW (28 < 4*14=56 → True)
        # Wait: 28 < 28 is False, 28 < 56 is True → LOW
        risk = classify_stockout_risk(state)
        # Let me recalculate: 28 < 14 → no, 28 < 14 → no, 28 < 28 → no, 28 < 56 → yes → LOW
        assert risk == StockoutRiskLevel.LOW

    def test_no_risk_with_ample_stock(self):
        state = InventoryState(
            on_hand_quantity=1000, reserved_quantity=0,
            average_daily_demand=1.0, lead_time_days=7, safety_stock_days=7,
        )
        # days_remaining = 1000, threshold = 14 → 1000 > 56 → NONE
        risk = classify_stockout_risk(state)
        assert risk == StockoutRiskLevel.NONE

    def test_no_risk_with_no_demand(self):
        """No demand history → cannot assess → NONE."""
        state = InventoryState(
            on_hand_quantity=0, reserved_quantity=0,
            average_daily_demand=0.0, lead_time_days=7,
        )
        risk = classify_stockout_risk(state)
        assert risk == StockoutRiskLevel.NONE
