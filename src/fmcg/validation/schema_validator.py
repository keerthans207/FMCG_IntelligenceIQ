"""
Record-level validation for FMCG data.

Validates individual records against JSON schemas defined in data/schemas/.
Used by the ingestion pipeline to separate valid records from rejected ones.
Does NOT require Spark — runs in pure Python for unit testability.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Lazy import jsonschema — it's used for validation but not always installed locally
try:
    from jsonschema import validate as _js_validate
    from jsonschema import ValidationError as _JSValidationError
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False
    _JSValidationError = Exception  # type: ignore[misc,assignment]


_SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "schemas"

# Cache loaded schemas
_schema_cache: dict[str, dict[str, Any]] = {}


def _load_schema(name: str) -> dict[str, Any]:
    """Load a JSON schema by dataset name (e.g. 'products')."""
    if name not in _schema_cache:
        path = _SCHEMA_DIR / f"{name}.schema.json"
        with open(path, "r", encoding="utf-8") as f:
            _schema_cache[name] = json.load(f)
    return _schema_cache[name]


def validate_single_record(
    dataset_name: str,
    record: dict[str, Any],
) -> tuple[bool, str | None]:
    """
    Validate a single record against its schema.

    Returns (is_valid, error_message).
    If jsonschema is not installed, falls back to a basic key-presence check.
    """
    schema = _load_schema(dataset_name)

    if _HAS_JSONSCHEMA:
        try:
            _js_validate(instance=record, schema=schema)
            return True, None
        except _JSValidationError as e:
            return False, str(e)
    else:
        # Fallback: check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in record:
                return False, f"Missing required field: {field}"
        return True, None


def validate_records(
    dataset_name: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate a list of records against their schema.

    Returns a summary dict:
        valid_count, invalid_count, rejected_records (list of {record, error}),
        duplicate_count
    """
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    duplicate_count = 0

    schema = _load_schema(dataset_name)
    # Determine the unique key field from schema properties
    # Look for a field ending in _id or _id itself
    unique_key = None
    for prop_name in schema.get("properties", {}):
        if prop_name.endswith("_id") and prop_name != "_id":
            unique_key = prop_name
            break

    for record in records:
        is_valid, error = validate_single_record(dataset_name, record)
        if not is_valid:
            rejected.append({"record": record, "error": error})
            continue

        # Duplicate detection on business key
        if unique_key and unique_key in record:
            key_val = str(record[unique_key])
            if key_val in seen_keys:
                duplicate_count += 1
                rejected.append({"record": record, "error": f"Duplicate {unique_key}: {key_val}"})
                continue
            seen_keys.add(key_val)

        valid.append(record)

    return {
        "dataset": dataset_name,
        "total": len(records),
        "valid_count": len(valid),
        "invalid_count": len(rejected),
        "duplicate_count": duplicate_count,
        "valid_records": valid,
        "rejected_records": rejected,
    }
