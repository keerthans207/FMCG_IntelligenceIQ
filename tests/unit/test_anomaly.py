"""
Unit tests for anomaly detection: demand spikes/drops, inventory anomalies.
"""

import pytest
from datetime import date

from fmcg.anomaly.detector import (
    DailySalesRecord,
    detect_demand_anomalies,
    detect_inventory_anomalies,
)


class TestDemandAnomalies:

    def test_spike_detected(self):
        """A sudden high demand should be flagged."""
        sales = []
        for i in range(30):
            sales.append(DailySalesRecord(
                date=date(2025, 6, 1 + i).isoformat(),
                sku_id="SKU00001",
                location_id="LOC0001",
                units_sold=10 + (i % 3),  # stable around 10-12
            ))
        # Day 31: spike to 50
        sales.append(DailySalesRecord(
            date="2025-07-01",
            sku_id="SKU00001",
            location_id="LOC0001",
            units_sold=50,
        ))
        anomalies = detect_demand_anomalies(sales, z_threshold=2.0)
        assert len(anomalies) >= 1
        assert anomalies[-1]["anomaly_type"] == "demand_spike"
        assert anomalies[-1]["z_score"] > 2.0

    def test_drop_detected(self):
        """A sudden demand drop should be flagged."""
        sales = []
        for i in range(30):
            sales.append(DailySalesRecord(
                date=date(2025, 6, 1 + i).isoformat(),
                sku_id="SKU00001",
                location_id="LOC0001",
                units_sold=50,
            ))
        # Day 31: drop to 5
        sales.append(DailySalesRecord(
            date="2025-07-01",
            sku_id="SKU00001",
            location_id="LOC0001",
            units_sold=5,
        ))
        anomalies = detect_demand_anomalies(sales, z_threshold=2.0)
        assert len(anomalies) >= 1
        assert any(a["anomaly_type"] == "demand_drop" for a in anomalies)

    def test_insufficient_history(self):
        """Fewer than min_history records → no anomalies."""
        sales = [
            DailySalesRecord("2025-06-01", "SKU00001", "LOC0001", 100),
        ]
        anomalies = detect_demand_anomalies(sales, min_history=14)
        assert len(anomalies) == 0

    def test_stable_demand_no_anomalies(self):
        """Uniform demand should produce no anomalies."""
        sales = [
            DailySalesRecord(date(2025, 6, 1 + i).isoformat(),
                             "SKU00001", "LOC0001", 10)
            for i in range(20)
        ]
        anomalies = detect_demand_anomalies(sales, z_threshold=2.5)
        assert len(anomalies) == 0

    def test_evidence_included(self):
        """Each anomaly should include explainable evidence."""
        sales = [
            DailySalesRecord(date(2025, 6, 1 + i).isoformat(),
                             "SKU00001", "LOC0001", 10)
            for i in range(20)
        ]
        sales.append(DailySalesRecord("2025-06-21", "SKU00001", "LOC0001", 100))
        anomalies = detect_demand_anomalies(sales, z_threshold=2.0)
        if anomalies:
            assert "evidence" in anomalies[-1]
            assert "z_score" in anomalies[-1]
            assert "mean_demand" in anomalies[-1]


class TestInventoryAnomalies:

    def test_negative_inventory_detected(self):
        """Negative on_hand after movement → critical anomaly."""
        movements = [
            {"movement_id": "MOV0000000001", "location_id": "LOC0001",
             "sku_id": "SKU00001", "batch_id": "BAT000001",
             "movement_type": "outbound", "quantity_change": -100,
             "on_hand_after": -5, "reference_id": "SALES-001"},
        ]
        anomalies = detect_inventory_anomalies(movements)
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_type"] == "negative_inventory"
        assert anomalies[0]["severity"] == "critical"

    def test_large_adjustment_detected(self):
        """Large adjustment → anomaly."""
        movements = [
            {"movement_id": "MOV0000000002", "location_id": "LOC0001",
             "sku_id": "SKU00001", "batch_id": "BAT000001",
             "movement_type": "adjustment", "quantity_change": 500,
             "on_hand_after": 600, "reference_id": "ADJ-002"},
        ]
        anomalies = detect_inventory_anomalies(movements)
        assert len(anomalies) >= 1
        assert any(a["anomaly_type"] == "stock_adjustment_anomaly" for a in anomalies)

    def test_normal_movement_no_anomaly(self):
        """Normal outbound movement with positive balance → no anomaly."""
        movements = [
            {"movement_id": "MOV0000000003", "location_id": "LOC0001",
             "sku_id": "SKU00001", "batch_id": "BAT000001",
             "movement_type": "outbound", "quantity_change": -10,
             "on_hand_after": 90, "reference_id": "SALES-003"},
        ]
        anomalies = detect_inventory_anomalies(movements)
        assert len(anomalies) == 0

    def test_empty_movements_no_error(self):
        anomalies = detect_inventory_anomalies([])
        assert anomalies == []
