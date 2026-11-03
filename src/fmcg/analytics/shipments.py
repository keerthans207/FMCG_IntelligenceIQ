"""
Shipment analytics: delivery duration, delays, supplier performance.

Pure Python implementations, unit-testable without Spark.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ShipmentRecord:
    """Shipment record with timestamps for analytics."""
    shipment_id: str
    origin_location_id: str
    destination_location_id: str
    dispatch_timestamp: datetime
    expected_delivery_timestamp: datetime
    actual_delivery_timestamp: datetime | None = None
    shipment_status: str = "pending"


def classify_shipment_delay(shipment: ShipmentRecord) -> dict[str, Any]:
    """
    Classify a shipment's delay status.

    Returns dict with:
        is_delayed: bool
        delay_hours: float (0 if on-time or not yet delivered)
        delivery_duration_hours: float | None (None if not delivered)
    """
    result: dict[str, Any] = {
        "shipment_id": shipment.shipment_id,
        "is_delayed": False,
        "delay_hours": 0.0,
        "delivery_duration_hours": None,
        "status": shipment.shipment_status,
    }

    if shipment.actual_delivery_timestamp is not None:
        # Delivered — calculate actual duration and delay
        duration = (shipment.actual_delivery_timestamp - shipment.dispatch_timestamp)
        duration_hours = duration.total_seconds() / 3600
        result["delivery_duration_hours"] = round(duration_hours, 2)

        delay = shipment.actual_delivery_timestamp - shipment.expected_delivery_timestamp
        delay_hours = delay.total_seconds() / 3600

        if delay_hours > 0:
            result["is_delayed"] = True
            result["delay_hours"] = round(delay_hours, 2)
        else:
            result["delay_hours"] = 0.0

    elif shipment.shipment_status in ("pending", "in_transit"):
        # Not yet delivered — check if overdue vs expected delivery
        now = datetime.now(timezone.utc)
        # Ensure timestamps are timezone-aware for comparison
        expected = shipment.expected_delivery_timestamp
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)

        if now > expected:
            overdue_hours = (now - expected).total_seconds() / 3600
            result["is_delayed"] = True
            result["delay_hours"] = round(overdue_hours, 2)
            result["status"] = "delayed"

    return result


def calculate_delivery_stats(shipments: list[ShipmentRecord]) -> dict[str, Any]:
    """
    Aggregate delivery statistics across a set of shipments.

    Returns average delivery duration, delay rate, average delay for
    delayed shipments, and counts by status.
    """
    total = len(shipments)
    delivered = 0
    delayed = 0
    total_duration = 0.0
    total_delay = 0.0
    status_counts: dict[str, int] = {}

    for s in shipments:
        info = classify_shipment_delay(s)
        status = info["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

        if info["delivery_duration_hours"] is not None:
            delivered += 1
            total_duration += info["delivery_duration_hours"]

        if info["is_delayed"]:
            delayed += 1
            total_delay += info["delay_hours"]

    return {
        "total_shipments": total,
        "delivered": delivered,
        "delayed": delayed,
        "on_time": delivered - delayed if delivered > 0 else 0,
        "delay_rate": round(delayed / delivered, 4) if delivered > 0 else 0.0,
        "avg_delivery_hours": round(total_duration / delivered, 2) if delivered > 0 else 0.0,
        "avg_delay_hours": round(total_delay / delayed, 2) if delayed > 0 else 0.0,
        "status_counts": status_counts,
    }
