"""
MongoDB idempotent write utilities.

Writes records using upsert (update-or-insert) keyed on the unique
business identifier to prevent duplicates on re-runs.
"""

from __future__ import annotations

from typing import Any, Iterable

from fmcg.config.settings import EnvSettings
from fmcg.database.connection import get_database


def _get_unique_key(collection_name: str) -> str:
    """Return the unique business key for a collection."""
    key_map = {
        "products": "sku_id",
        "locations": "location_id",
        "suppliers": "supplier_id",
        "batches": "batch_id",
        "sales_transactions": "transaction_id",
        "inventory_snapshots": "snapshot_id",
        "stock_movements": "movement_id",
        "shipments": "shipment_id",
        "analytics_alerts": "alert_id",
        "forecasts": "forecast_id",
        "pipeline_runs": "run_id",
    }
    return key_map.get(collection_name, "_id")


def bulk_upsert(
    collection_name: str,
    records: Iterable[dict[str, Any]],
    unique_key: str | None = None,
    settings: EnvSettings | None = None,
) -> dict[str, int]:
    """
    Upsert records into a MongoDB collection using the unique business key.

    Returns a summary dict with counts: upserted, matched, errors.
    Idempotent — re-running with the same data updates existing records.
    """
    db = get_database(settings)
    coll = db[collection_name]
    key_field = unique_key or _get_unique_key(collection_name)

    try:
        from pymongo import UpdateOne
        from pymongo.errors import BulkWriteError
    except ImportError:
        raise ImportError("pymongo is required for MongoDB writes")

    operations: list[UpdateOne] = []
    record_list = list(records)

    for record in record_list:
        filter_doc = {key_field: record[key_field]}
        update_doc = {"$set": record}
        operations.append(UpdateOne(filter_doc, update_doc, upsert=True))

    if not operations:
        return {"upserted": 0, "matched": 0, "errors": 0, "total": 0}

    try:
        result = coll.bulk_write(operations, ordered=False)
        return {
            "upserted": result.upserted_count,
            "matched": result.matched_count,
            "modified": result.modified_count,
            "errors": 0,
            "total": len(record_list),
        }
    except BulkWriteError as e:
        # Partial success — some writes may have gone through
        write_errors = e.details.get("writeErrors", [])
        return {
            "upserted": e.details.get("nUpserted", 0),
            "matched": e.details.get("nMatched", 0),
            "modified": e.details.get("nModified", 0),
            "errors": len(write_errors),
            "total": len(record_list),
            "error_details": write_errors[:5],
        }


def write_records_to_mongo(
    collection_name: str,
    records: Iterable[dict[str, Any]],
    unique_key: str | None = None,
    settings: EnvSettings | None = None,
) -> dict[str, int]:
    """Convenience wrapper around bulk_upsert."""
    return bulk_upsert(collection_name, records, unique_key, settings)
