"""
Pydantic models for API request/response validation and pagination.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic pagination wrapper
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated API response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str | None = None
    timestamp: str


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class Product(BaseModel):
    sku_id: str
    product_name: str
    brand: str | None = None
    category: str | None = None
    unit_size: str | None = None
    unit_cost: float | None = None
    selling_price: float | None = None
    shelf_life_days: int | None = None


class Location(BaseModel):
    location_id: str
    location_name: str
    location_type: str | None = None
    city: str | None = None
    state: str | None = None
    region: str | None = None


class InventoryItem(BaseModel):
    location_id: str
    sku_id: str
    batch_id: str
    product_name: str | None = None
    on_hand_quantity: int
    reserved_quantity: int
    available_stock: int
    days_remaining: float | None = None
    stockout_risk: str | None = None


class ExpiryItem(BaseModel):
    batch_id: str
    sku_id: str
    product_name: str | None = None
    expiry_date: str
    days_until_expiry: int
    available_stock: int
    expiry_risk: str


class Shipment(BaseModel):
    shipment_id: str
    origin_location_id: str
    destination_location_id: str
    dispatch_timestamp: str | None = None
    expected_delivery_timestamp: str | None = None
    actual_delivery_timestamp: str | None = None
    shipment_status: str
    is_delayed: bool = False
    delay_hours: float = 0.0


class Forecast(BaseModel):
    forecast_date: str
    sku_id: str
    location_id: str
    predicted_units: float


class Alert(BaseModel):
    alert_id: str
    alert_type: str
    severity: str
    sku_id: str | None = None
    location_id: str | None = None
    alert_description: str
    recommendation: str
    acknowledged: bool = False
    created_at: str | None = None


class PipelineRun(BaseModel):
    run_id: str
    start_time: str
    end_time: str | None = None
    status: str
    records_ingested: int = 0
    records_processed: int = 0
    records_rejected: int = 0
    execution_duration: float = 0.0
    error_message: str | None = None


class DashboardSummary(BaseModel):
    """Executive dashboard summary."""
    total_skus: int
    total_locations: int
    total_inventory_units: int
    stockout_risk_products: int
    expiry_risk_batches: int
    delayed_shipments: int
    latest_pipeline_status: str | None = None
    latest_pipeline_run_id: str | None = None


class ReplenishmentRecommendation(BaseModel):
    sku_id: str
    location_id: str
    product_name: str | None = None
    available_stock: int
    avg_daily_demand: float
    days_remaining: float | None = None
    reorder_quantity: int
    stockout_risk: str
