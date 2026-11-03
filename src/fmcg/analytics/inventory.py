"""
Inventory intelligence calculations.

Pure Python implementations of the inventory formulas described in the
project spec. These are unit-testable without Spark. The Spark jobs
implement the same logic at scale using Spark SQL / DataFrames.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class StockoutRiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class InventoryState:
    """Current inventory state for a single SKU/location combination."""
    on_hand_quantity: int
    reserved_quantity: int
    incoming_quantity: int = 0  # confirmed inbound stock not yet received
    average_daily_demand: float = 0.0
    lead_time_days: int = 0
    safety_stock_days: int = 7


def calculate_available_stock(state: InventoryState) -> int:
    """
    Available stock = on_hand - reserved.

    This is the sellable inventory. Multiple batches and locations are
    aggregated by summing available stock across all batches/locations
    for a given SKU.
    """
    return max(0, state.on_hand_quantity - state.reserved_quantity)


def calculate_days_remaining(state: InventoryState) -> float | None:
    """
    Days of stock remaining = available_stock / average_daily_demand.

    Returns None when demand history is insufficient (zero or negative demand)
    to avoid division by zero.
    """
    available = calculate_available_stock(state)
    if state.average_daily_demand is None or state.average_daily_demand <= 0:
        return None  # insufficient demand history
    return round(available / state.average_daily_demand, 1)


def calculate_reorder_quantity(
    state: InventoryState,
    forecast_demand_during_lead_time: float = 0.0,
    safety_stock: int = 0,
    min_order_quantity: int = 0,
    reorder_multiple: int = 1,
) -> int:
    """
    Reorder quantity formula:

        reorder_quantity = max(
            0,
            forecast_demand_during_lead_time
            + safety_stock
            - available_stock
            - confirmed_incoming_stock
        )

    Then rounded up to the nearest reorder_multiple, with a floor of
    min_order_quantity (0 if no minimum is configured).

    Does NOT treat current stock, reserved stock, and incoming stock
    as interchangeable — each has a distinct role.
    """
    available = calculate_available_stock(state)

    raw_quantity = (
        forecast_demand_during_lead_time
        + safety_stock
        - available
        - state.incoming_quantity
    )
    reorder_qty = max(0, int(raw_quantity))

    # Apply reorder multiple
    if reorder_multiple > 1 and reorder_qty > 0:
        reorder_qty = ((reorder_qty + reorder_multiple - 1) // reorder_multiple) * reorder_multiple

    # Apply minimum order quantity
    if reorder_qty > 0:
        reorder_qty = max(reorder_qty, min_order_quantity)

    return reorder_qty


def classify_stockout_risk(state: InventoryState) -> StockoutRiskLevel:
    """
    Classify stockout risk based on days of stock remaining vs lead time.

    - CRITICAL: days_remaining < lead_time_days (cannot replenish in time)
    - HIGH:     days_remaining < lead_time_days + safety_stock_days
    - MEDIUM:   days_remaining < 2 * (lead_time_days + safety_stock_days)
    - LOW:      days_remaining < 4 * (lead_time_days + safety_stock_days)
    - NONE:     ample stock
    """
    days_remaining = calculate_days_remaining(state)

    if days_remaining is None:
        # No demand history — cannot assess risk meaningfully
        return StockoutRiskLevel.NONE

    threshold = state.lead_time_days + state.safety_stock_days

    if days_remaining < state.lead_time_days:
        return StockoutRiskLevel.CRITICAL
    elif days_remaining < threshold:
        return StockoutRiskLevel.HIGH
    elif days_remaining < 2 * threshold:
        return StockoutRiskLevel.MEDIUM
    elif days_remaining < 4 * threshold:
        return StockoutRiskLevel.LOW
    else:
        return StockoutRiskLevel.NONE
