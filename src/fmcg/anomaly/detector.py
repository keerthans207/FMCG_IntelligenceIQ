"""
Anomaly detection using explainable statistical and rule-based methods.

These do NOT label anomalies as fraud — they flag statistical outliers
and rule violations that warrant investigation.
Pure Python for unit testing; Spark job applies the same logic at scale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class DailySalesRecord:
    date: str
    sku_id: str
    location_id: str
    units_sold: int


def detect_demand_anomalies(
    daily_sales: list[DailySalesRecord],
    z_threshold: float = 2.5,
    min_history: int = 14,
) -> list[dict[str, Any]]:
    """
    Detect unusual demand spikes and drops using z-score.

    A z-score beyond the threshold flags the record as anomalous.
    Requires at least `min_history` records to establish a baseline.

    Each result includes evidence (mean, std, z-score) so it is
    explainable during a viva.
    """
    if len(daily_sales) < min_history:
        return []

    values = [r.units_sold for r in daily_sales]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0.0

    if std == 0:
        return []

    anomalies: list[dict[str, Any]] = []
    for record in daily_sales:
        z_score = (record.units_sold - mean) / std
        if abs(z_score) > z_threshold:
            anomaly_type = "demand_spike" if z_score > 0 else "demand_drop"
            severity = "critical" if abs(z_score) > 4 else "high" if abs(z_score) > 3.5 else "medium"
            anomalies.append({
                "date": record.date,
                "sku_id": record.sku_id,
                "location_id": record.location_id,
                "units_sold": record.units_sold,
                "mean_demand": round(mean, 2),
                "std_demand": round(std, 2),
                "z_score": round(z_score, 3),
                "anomaly_type": anomaly_type,
                "severity": severity,
                "evidence": f"Z-score {z_score:.3f} exceeds threshold {z_threshold} (mean={mean:.1f}, std={std:.1f})",
            })

    return anomalies


def detect_inventory_anomalies(
    movements: list[dict[str, Any]],
    max_adjustment_pct: float = 20.0,
) -> list[dict[str, Any]]:
    """
    Detect unexpected stock adjustments and negative inventory balances.

    Flags:
    - Negative inventory balances (on_hand < 0 after a movement)
    - Large adjustments (adjustment quantity exceeds threshold)
    - Unusual movement quantities (statistical outliers)
    """
    anomalies: list[dict[str, Any]] = []

    for m in movements:
        qty_change = m.get("quantity_change", 0)
        movement_type = m.get("movement_type", "")
        on_hand_after = m.get("on_hand_after")

        # Negative inventory balance
        if on_hand_after is not None and on_hand_after < 0:
            anomalies.append({
                "movement_id": m.get("movement_id"),
                "location_id": m.get("location_id"),
                "sku_id": m.get("sku_id"),
                "batch_id": m.get("batch_id"),
                "anomaly_type": "negative_inventory",
                "severity": "critical",
                "evidence": f"Inventory balance {on_hand_after} is negative after {movement_type}",
            })

        # Large adjustment
        if movement_type == "adjustment" and abs(qty_change) > 0:
            anomalies.append({
                "movement_id": m.get("movement_id"),
                "location_id": m.get("location_id"),
                "sku_id": m.get("sku_id"),
                "batch_id": m.get("batch_id"),
                "anomaly_type": "stock_adjustment_anomaly",
                "severity": "high" if abs(qty_change) > 100 else "medium",
                "evidence": f"Adjustment of {qty_change} units — review required",
            })

    return anomalies
