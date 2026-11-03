"""
Unit tests for shipment analytics: delays, delivery stats, supplier performance.
"""

import pytest
from datetime import datetime, timedelta, timezone

from fmcg.analytics.shipments import (
    ShipmentRecord,
    classify_shipment_delay,
    calculate_delivery_stats,
)


def _ts(days_ago: float, hours: float = 0) -> datetime:
    """Helper: create a UTC datetime N days/hours ago."""
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours)


class TestShipmentDelay:

    def test_on_time_delivery(self):
        """Delivered before or at expected time → not delayed."""
        dispatch = _ts(10)
        expected = _ts(8)
        actual = _ts(8, hours=2)  # 2 hours earlier than expected = on time
        shipment = ShipmentRecord(
            shipment_id="SHP00000001",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=actual,
            shipment_status="delivered",
        )
        result = classify_shipment_delay(shipment)
        assert not result["is_delayed"]
        assert result["delay_hours"] == 0.0
        assert result["delivery_duration_hours"] is not None

    def test_delayed_delivery(self):
        """Delivered after expected time → delayed."""
        dispatch = _ts(10)
        expected = _ts(8)
        actual = _ts(7, hours=-12)  # 12 hours after expected
        shipment = ShipmentRecord(
            shipment_id="SHP00000002",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=actual,
            shipment_status="delivered",
        )
        result = classify_shipment_delay(shipment)
        assert result["is_delayed"]
        assert result["delay_hours"] > 0

    def test_pending_shipment_not_overdue(self):
        """Pending shipment within expected window → not delayed."""
        dispatch = _ts(1)
        expected = datetime.now(timezone.utc) + timedelta(days=2)
        shipment = ShipmentRecord(
            shipment_id="SHP00000003",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=None,
            shipment_status="in_transit",
        )
        result = classify_shipment_delay(shipment)
        assert not result["is_delayed"]

    def test_overdue_shipment_flagged(self):
        """In-transit past expected time → flagged as delayed."""
        dispatch = _ts(10)
        expected = _ts(5)  # expected 5 days ago
        shipment = ShipmentRecord(
            shipment_id="SHP00000004",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=None,
            shipment_status="in_transit",
        )
        result = classify_shipment_delay(shipment)
        assert result["is_delayed"]
        assert result["delay_hours"] > 0

    def test_cancelled_shipment_not_delayed(self):
        dispatch = _ts(5)
        expected = _ts(3)
        shipment = ShipmentRecord(
            shipment_id="SHP00000005",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=None,
            shipment_status="cancelled",
        )
        result = classify_shipment_delay(shipment)
        # Cancelled is neither pending nor in_transit, so no overdue check
        assert not result["is_delayed"]

    def test_delivery_duration_calculated(self):
        """Delivery duration = actual - dispatch."""
        dispatch = datetime(2025, 6, 10, 10, 0, tzinfo=timezone.utc)
        expected = datetime(2025, 6, 13, 10, 0, tzinfo=timezone.utc)
        actual = datetime(2025, 6, 13, 8, 0, tzinfo=timezone.utc)  # 2h early
        shipment = ShipmentRecord(
            shipment_id="SHP00000006",
            origin_location_id="LOC0001",
            destination_location_id="LOC0002",
            dispatch_timestamp=dispatch,
            expected_delivery_timestamp=expected,
            actual_delivery_timestamp=actual,
            shipment_status="delivered",
        )
        result = classify_shipment_delay(shipment)
        # Duration = 3 days - 2 hours = 70 hours
        assert result["delivery_duration_hours"] == 70.0


class TestDeliveryStats:

    def test_stats_mixed_shipments(self):
        dispatch = _ts(20)
        shipments = [
            # On-time delivery (delivered 2h before expected)
            ShipmentRecord("SHP00000001", "LOC0001", "LOC0002", dispatch,
                           _ts(15), _ts(15, hours=2), "delivered"),
            # Delayed delivery
            ShipmentRecord("SHP00000002", "LOC0001", "LOC0003", dispatch,
                           _ts(12), _ts(10), "delayed"),
            # In transit (not yet overdue)
            ShipmentRecord("SHP00000003", "LOC0001", "LOC0004", _ts(1),
                           datetime.now(timezone.utc) + timedelta(days=2),
                           None, "in_transit"),
        ]
        stats = calculate_delivery_stats(shipments)
        assert stats["total_shipments"] == 3
        assert stats["delivered"] == 2
        assert stats["delayed"] == 1
        assert stats["delay_rate"] == 0.5  # 1 out of 2 delivered
        assert stats["avg_delivery_hours"] > 0

    def test_stats_all_empty(self):
        stats = calculate_delivery_stats([])
        assert stats["total_shipments"] == 0
        assert stats["avg_delivery_hours"] == 0.0
