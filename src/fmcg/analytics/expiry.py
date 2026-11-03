"""
Expiry analytics and FEFO (First Expired, First Out) logic.

Pure Python implementations, unit-testable without Spark.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any


class ExpiryRiskLevel(str, Enum):
    EXPIRED = "expired"
    CRITICAL = "critical"       # expires within 7 days
    APPROACHING = "approaching"  # expires within 30 days
    HEALTHY = "healthy"          # more than 30 days remaining


# Thresholds in days
EXPIRED_THRESHOLD = 0
CRITICAL_THRESHOLD = 7
APPROACHING_THRESHOLD = 30


@dataclass
class BatchInfo:
    """Batch with calculated expiry information."""
    batch_id: str
    sku_id: str
    expiry_date: date
    on_hand_quantity: int
    reserved_quantity: int = 0


def days_until_expiry(expiry_date: date, reference_date: date | None = None) -> int:
    """
    Calculate days until expiry from a reference date.

    Defaults to today (UTC) if reference_date is not provided.
    Returns a negative number if already expired.
    """
    ref = reference_date or datetime.now(timezone.utc).date()
    delta = expiry_date - ref
    return delta.days


def classify_expiry_risk(
    expiry_date: date,
    reference_date: date | None = None,
) -> ExpiryRiskLevel:
    """
    Classify a batch's expiry risk level.

    An expiry alert indicates risk of waste — it does NOT prove that
    stock was actually wasted.
    """
    days = days_until_expiry(expiry_date, reference_date)

    if days <= EXPIRED_THRESHOLD:
        return ExpiryRiskLevel.EXPIRED
    elif days <= CRITICAL_THRESHOLD:
        return ExpiryRiskLevel.CRITICAL
    elif days <= APPROACHING_THRESHOLD:
        return ExpiryRiskLevel.APPROACHING
    else:
        return ExpiryRiskLevel.HEALTHY


def rank_batches_fefo(
    batches: list[BatchInfo],
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Rank batches by FEFO (First Expired, First Out) priority.

    Returns a list of dicts sorted by expiry date ascending:
        {batch_id, sku_id, expiry_date, days_until_expiry,
         available_quantity, risk_level}

    Already-expired batches are still included but flagged.
    """
    ranked = []
    for batch in batches:
        days = days_until_expiry(batch.expiry_date, reference_date)
        risk = classify_expiry_risk(batch.expiry_date, reference_date)
        available = max(0, batch.on_hand_quantity - batch.reserved_quantity)
        ranked.append({
            "batch_id": batch.batch_id,
            "sku_id": batch.sku_id,
            "expiry_date": batch.expiry_date.isoformat(),
            "days_until_expiry": days,
            "available_quantity": available,
            "risk_level": risk.value,
        })

    ranked.sort(key=lambda b: b["expiry_date"])
    return ranked


def calculate_expiry_exposure(
    batches: list[BatchInfo],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """
    Calculate total inventory exposure by expiry risk level.

    Returns a summary dict with quantities and counts per risk level.
    """
    summary: dict[str, Any] = {
        "total_batches": len(batches),
        "total_quantity": 0,
        "expired_quantity": 0,
        "critical_quantity": 0,
        "approaching_quantity": 0,
        "healthy_quantity": 0,
        "by_risk": {},
    }

    for batch in batches:
        risk = classify_expiry_risk(batch.expiry_date, reference_date)
        available = max(0, batch.on_hand_quantity - batch.reserved_quantity)
        summary["total_quantity"] += available

        if risk == ExpiryRiskLevel.EXPIRED:
            summary["expired_quantity"] += available
        elif risk == ExpiryRiskLevel.CRITICAL:
            summary["critical_quantity"] += available
        elif risk == ExpiryRiskLevel.APPROACHING:
            summary["approaching_quantity"] += available
        else:
            summary["healthy_quantity"] += available

        key = risk.value
        if key not in summary["by_risk"]:
            summary["by_risk"][key] = {"batch_count": 0, "quantity": 0}
        summary["by_risk"][key]["batch_count"] += 1
        summary["by_risk"][key]["quantity"] += available

    return summary
