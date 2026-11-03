"""
Data access service layer.

Queries MongoDB for operational data and published analytical results.
The API layer calls these functions — they are the bridge between
MongoDB and FastAPI endpoints.
"""

from __future__ import annotations

from typing import Any

from fmcg.config.settings import EnvSettings
from fmcg.database.connection import get_database


def _get_collection(settings: EnvSettings | None, name: str):
    """Get a MongoDB collection."""
    db = get_database(settings)
    return db[name]


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def get_products(
    settings: EnvSettings | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    coll = _get_collection(settings, "products")
    query: dict = {}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"product_name": {"$regex": search, "$options": "i"}},
            {"brand": {"$regex": search, "$options": "i"}},
        ]
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).skip(skip).limit(page_size))
    # Convert ObjectId to string
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

def get_locations(
    settings: EnvSettings | None = None,
    location_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    coll = _get_collection(settings, "locations")
    query: dict = {}
    if location_type:
        query["location_type"] = location_type
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).skip(skip).limit(page_size))
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def get_inventory(
    settings: EnvSettings | None = None,
    sku_id: str | None = None,
    location_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    coll = _get_collection(settings, "inventory_snapshots")
    query: dict = {}
    if sku_id:
        query["sku_id"] = sku_id
    if location_id:
        query["location_id"] = location_id

    # Get latest snapshot per sku/location/batch
    pipeline = [
        {"$match": query} if query else {"$match": {}},
        {"$sort": {"snapshot_timestamp": -1}},
        {"$group": {
            "_id": {
                "location_id": "$location_id",
                "sku_id": "$sku_id",
                "batch_id": "$batch_id",
            },
            "snapshot_id": {"$first": "$snapshot_id"},
            "snapshot_timestamp": {"$first": "$snapshot_timestamp"},
            "location_id": {"$first": "$location_id"},
            "sku_id": {"$first": "$sku_id"},
            "batch_id": {"$first": "$batch_id"},
            "on_hand_quantity": {"$first": "$on_hand_quantity"},
            "reserved_quantity": {"$first": "$reserved_quantity"},
        }},
    ]
    items = list(coll.aggregate(pipeline))

    # Add available stock
    for item in items:
        item["available_stock"] = max(0,
            item.get("on_hand_quantity", 0) - item.get("reserved_quantity", 0))
        item.pop("_id", None)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Analytics results (from Spark → MongoDB publication)
# ---------------------------------------------------------------------------

def get_expiry_items(
    settings: EnvSettings | None = None,
    risk_level: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Get expiry analysis results from MongoDB analytics collection."""
    coll = _get_collection(settings, "analytics_alerts")
    query: dict = {"alert_type": "expiry_risk"}
    if risk_level:
        query["severity"] = risk_level
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).skip(skip).limit(page_size))
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_shipments(
    settings: EnvSettings | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    coll = _get_collection(settings, "shipments")
    query: dict = {}
    if status:
        query["shipment_status"] = status
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).skip(skip).limit(page_size))
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_forecasts(
    settings: EnvSettings | None = None,
    sku_id: str | None = None,
    location_id: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    coll = _get_collection(settings, "forecasts")
    query: dict = {}
    if sku_id:
        query["sku_id"] = sku_id
    if location_id:
        query["location_id"] = location_id
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).sort("forecast_date", 1).skip(skip).limit(page_size))
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_anomalies(
    settings: EnvSettings | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    coll = _get_collection(settings, "analytics_alerts")
    query: dict = {}
    if severity:
        query["severity"] = severity
    total = coll.count_documents(query)
    skip = (page - 1) * page_size
    items = list(coll.find(query).skip(skip).limit(page_size))
    for item in items:
        item["_id"] = str(item["_id"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_pipeline_runs(
    settings: EnvSettings | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    coll = _get_collection(settings, "pipeline_runs")
    items = list(coll.find().sort("start_time", -1).limit(limit))
    for item in items:
        item["_id"] = str(item["_id"])
    return {"items": items, "total": len(items)}


def get_dashboard_summary(settings: EnvSettings | None = None) -> dict[str, Any]:
    """Aggregate summary metrics for the executive dashboard."""
    db = get_database(settings)

    total_skus = db["products"].count_documents({})
    total_locations = db["locations"].count_documents({})
    total_inventory = 0

    # Sum latest available stock
    pipeline = [
        {"$sort": {"snapshot_timestamp": -1}},
        {"$group": {
            "_id": {"loc": "$location_id", "sku": "$sku_id", "batch": "$batch_id"},
            "on_hand": {"$first": "$on_hand_quantity"},
            "reserved": {"$first": "$reserved_quantity"},
        }},
    ]
    for doc in db["inventory_snapshots"].aggregate(pipeline):
        total_inventory += max(0, doc.get("on_hand", 0) - doc.get("reserved", 0))

    stockout_risk = db["analytics_alerts"].count_documents({
        "alert_type": "stockout_risk", "acknowledged": False,
    })
    expiry_risk = db["analytics_alerts"].count_documents({
        "alert_type": "expiry_risk", "acknowledged": False,
    })
    delayed = db["shipments"].count_documents({"shipment_status": "delayed"})

    # Latest pipeline run
    latest = db["pipeline_runs"].find_one(sort=[("start_time", -1)])
    latest_status = latest.get("status") if latest else None
    latest_run_id = latest.get("run_id") if latest else None

    return {
        "total_skus": total_skus,
        "total_locations": total_locations,
        "total_inventory_units": total_inventory,
        "stockout_risk_products": stockout_risk,
        "expiry_risk_batches": expiry_risk,
        "delayed_shipments": delayed,
        "latest_pipeline_status": latest_status,
        "latest_pipeline_run_id": latest_run_id,
    }
