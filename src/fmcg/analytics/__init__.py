"""Analytics calculations: inventory, expiry, shipment, anomaly logic."""
from fmcg.analytics.inventory import (
    calculate_available_stock,
    calculate_days_remaining,
    calculate_reorder_quantity,
    classify_stockout_risk,
)
from fmcg.analytics.expiry import classify_expiry_risk, rank_batches_fefo
from fmcg.analytics.shipments import classify_shipment_delay, calculate_delivery_stats

__all__ = [
    "calculate_available_stock",
    "calculate_days_remaining",
    "calculate_reorder_quantity",
    "classify_stockout_risk",
    "classify_expiry_risk",
    "rank_batches_fefo",
    "classify_shipment_delay",
    "calculate_delivery_stats",
]
