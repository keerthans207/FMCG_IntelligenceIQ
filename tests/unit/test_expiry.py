"""
Unit tests for expiry analytics and FEFO logic.
"""

import pytest
from datetime import date, timedelta

from fmcg.analytics.expiry import (
    ExpiryRiskLevel,
    days_until_expiry,
    classify_expiry_risk,
    rank_batches_fefo,
    calculate_expiry_exposure,
    BatchInfo,
)


class TestExpiryRisk:

    def test_expired_batch(self):
        ref = date(2025, 6, 15)
        exp = date(2025, 6, 10)
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.EXPIRED

    def test_critical_expiry(self):
        """Expires within 7 days → critical."""
        ref = date(2025, 6, 15)
        exp = date(2025, 6, 20)  # 5 days away
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.CRITICAL

    def test_approaching_expiry(self):
        """Expires within 30 days (but > 7) → approaching."""
        ref = date(2025, 6, 15)
        exp = date(2025, 7, 5)  # 20 days away
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.APPROACHING

    def test_healthy_stock(self):
        """Expires > 30 days → healthy."""
        ref = date(2025, 6, 15)
        exp = date(2025, 12, 15)  # ~183 days away
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.HEALTHY

    def test_exactly_7_days(self):
        """Exactly 7 days is critical (boundary)."""
        ref = date(2025, 6, 15)
        exp = ref + timedelta(days=7)
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.CRITICAL

    def test_exactly_30_days(self):
        """Exactly 30 days is approaching (boundary)."""
        ref = date(2025, 6, 15)
        exp = ref + timedelta(days=30)
        assert classify_expiry_risk(exp, ref) == ExpiryRiskLevel.APPROACHING


class TestDaysUntilExpiry:

    def test_positive_days(self):
        ref = date(2025, 6, 15)
        exp = date(2025, 6, 20)
        assert days_until_expiry(exp, ref) == 5

    def test_negative_days_expired(self):
        ref = date(2025, 6, 15)
        exp = date(2025, 6, 10)
        assert days_until_expiry(exp, ref) == -5

    def test_zero_days(self):
        ref = date(2025, 6, 15)
        exp = date(2025, 6, 15)
        assert days_until_expiry(exp, ref) == 0


class TestFEFORanking:

    def test_fefo_sorts_by_expiry_ascending(self):
        """Batches with earliest expiry come first in FEFO."""
        batches = [
            BatchInfo(batch_id="BAT000003", sku_id="SKU00001",
                      expiry_date=date(2025, 8, 15), on_hand_quantity=100),
            BatchInfo(batch_id="BAT000001", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 20), on_hand_quantity=50),
            BatchInfo(batch_id="BAT000002", sku_id="SKU00001",
                      expiry_date=date(2025, 7, 10), on_hand_quantity=75),
        ]
        ranked = rank_batches_fefo(batches, reference_date=date(2025, 6, 15))
        assert ranked[0]["batch_id"] == "BAT000001"  # earliest expiry
        assert ranked[1]["batch_id"] == "BAT000002"
        assert ranked[2]["batch_id"] == "BAT000003"

    def test_fefo_includes_available_quantity(self):
        batches = [
            BatchInfo(batch_id="BAT000001", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 20),
                      on_hand_quantity=100, reserved_quantity=30),
        ]
        ranked = rank_batches_fefo(batches, reference_date=date(2025, 6, 15))
        assert ranked[0]["available_quantity"] == 70

    def test_fefo_flags_expired_batches(self):
        batches = [
            BatchInfo(batch_id="BAT000001", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 10), on_hand_quantity=50),
        ]
        ranked = rank_batches_fefo(batches, reference_date=date(2025, 6, 15))
        assert ranked[0]["risk_level"] == "expired"
        assert ranked[0]["days_until_expiry"] == -5


class TestExpiryExposure:

    def test_exposure_summary(self):
        ref = date(2025, 6, 15)
        batches = [
            BatchInfo(batch_id="BAT000001", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 10), on_hand_quantity=50),   # expired
            BatchInfo(batch_id="BAT000002", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 20), on_hand_quantity=100),  # critical
            BatchInfo(batch_id="BAT000003", sku_id="SKU00001",
                      expiry_date=date(2025, 12, 15), on_hand_quantity=200),  # healthy
        ]
        result = calculate_expiry_exposure(batches, ref)
        assert result["total_batches"] == 3
        assert result["total_quantity"] == 350
        assert result["expired_quantity"] == 50
        assert result["critical_quantity"] == 100
        assert result["healthy_quantity"] == 200

    def test_reserved_quantity_excluded(self):
        ref = date(2025, 6, 15)
        batches = [
            BatchInfo(batch_id="BAT000001", sku_id="SKU00001",
                      expiry_date=date(2025, 6, 10),
                      on_hand_quantity=100, reserved_quantity=30),
        ]
        result = calculate_expiry_exposure(batches, ref)
        # Available = 70, all expired
        assert result["expired_quantity"] == 70
