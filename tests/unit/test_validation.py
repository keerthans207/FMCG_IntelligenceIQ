"""
Unit tests for data validation: schema validation, duplicate detection,
and timestamp conversion.

These tests run without Spark or MongoDB — pure Python only.
"""

import pytest
from datetime import datetime, timezone

from fmcg.validation.schema_validator import validate_records, validate_single_record


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Tests for individual record schema validation."""

    def test_valid_product(self):
        record = {
            "sku_id": "SKU00001",
            "product_name": "FreshMart Beverages 1",
            "brand": "FreshMart",
            "category": "Beverages",
            "unit_size": "1L",
            "unit_cost": 25.0,
            "selling_price": 40.0,
            "shelf_life_days": 365,
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_single_record("products", record)
        assert is_valid, f"Expected valid, got error: {error}"

    def test_product_missing_required_field(self):
        record = {
            "sku_id": "SKU00001",
            "product_name": "FreshMart Beverages 1",
            # Missing category, unit_cost, selling_price, shelf_life_days, created_at
        }
        is_valid, error = validate_single_record("products", record)
        assert not is_valid, "Should be invalid — missing required fields"

    def test_product_invalid_sku_format(self):
        record = {
            "sku_id": "INVALID",
            "product_name": "Test Product",
            "brand": "TestBrand",
            "category": "Snacks",
            "unit_size": "100g",
            "unit_cost": 10.0,
            "selling_price": 20.0,
            "shelf_life_days": 180,
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_single_record("products", record)
        assert not is_valid, "Invalid SKU format should fail"

    def test_product_invalid_category(self):
        record = {
            "sku_id": "SKU00001",
            "product_name": "Test Product",
            "brand": "TestBrand",
            "category": "Electronics",  # Not in enum
            "unit_size": "100g",
            "unit_cost": 10.0,
            "selling_price": 20.0,
            "shelf_life_days": 180,
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_single_record("products", record)
        assert not is_valid

    def test_product_negative_cost(self):
        record = {
            "sku_id": "SKU00001",
            "product_name": "Test Product",
            "brand": "TestBrand",
            "category": "Snacks",
            "unit_size": "100g",
            "unit_cost": -5.0,
            "selling_price": 20.0,
            "shelf_life_days": 180,
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_single_record("products", record)
        assert not is_valid

    def test_valid_sales_transaction(self):
        record = {
            "transaction_id": "TXN0000000001",
            "transaction_timestamp": "2025-06-15T14:30:00Z",
            "sku_id": "SKU00001",
            "store_id": "LOC0001",
            "units_sold": 5,
            "unit_price": 40.0,
            "promotion_flag": False,
        }
        is_valid, error = validate_single_record("sales_transactions", record)
        assert is_valid, f"Expected valid: {error}"

    def test_sales_transaction_zero_units(self):
        record = {
            "transaction_id": "TXN0000000002",
            "transaction_timestamp": "2025-06-15T14:30:00Z",
            "sku_id": "SKU00001",
            "store_id": "LOC0001",
            "units_sold": 0,  # Minimum is 1
            "unit_price": 40.0,
            "promotion_flag": False,
        }
        is_valid, error = validate_single_record("sales_transactions", record)
        assert not is_valid

    def test_shipment_null_actual_delivery(self):
        """Shipments in transit have null actual_delivery_timestamp."""
        record = {
            "shipment_id": "SHP00000001",
            "origin_location_id": "LOC0001",
            "destination_location_id": "LOC0002",
            "dispatch_timestamp": "2025-06-15T10:00:00Z",
            "expected_delivery_timestamp": "2025-06-18T10:00:00Z",
            "actual_delivery_timestamp": None,
            "shipment_status": "in_transit",
        }
        is_valid, error = validate_single_record("shipments", record)
        assert is_valid, f"Expected valid: {error}"


# ---------------------------------------------------------------------------
# Duplicate detection tests
# ---------------------------------------------------------------------------

class TestDuplicateDetection:

    def test_detect_duplicate_transaction_ids(self):
        records = [
            {"transaction_id": "TXN0000000001", "transaction_timestamp": "2025-06-15T10:00:00Z",
             "sku_id": "SKU00001", "store_id": "LOC0001", "units_sold": 5,
             "unit_price": 10.0, "promotion_flag": False},
            {"transaction_id": "TXN0000000002", "transaction_timestamp": "2025-06-15T11:00:00Z",
             "sku_id": "SKU00001", "store_id": "LOC0001", "units_sold": 3,
             "unit_price": 10.0, "promotion_flag": False},
            {"transaction_id": "TXN0000000001", "transaction_timestamp": "2025-06-15T12:00:00Z",
             "sku_id": "SKU00002", "store_id": "LOC0002", "units_sold": 7,
             "unit_price": 15.0, "promotion_flag": True},
        ]
        result = validate_records("sales_transactions", records)
        assert result["total"] == 3
        assert result["valid_count"] == 2
        assert result["duplicate_count"] == 1
        assert result["invalid_count"] == 1

    def test_no_duplicates_when_all_unique(self):
        records = [
            {"transaction_id": f"TXN{i:010d}", "transaction_timestamp": "2025-06-15T10:00:00Z",
             "sku_id": "SKU00001", "store_id": "LOC0001", "units_sold": 5,
             "unit_price": 10.0, "promotion_flag": False}
            for i in range(1, 101)
        ]
        result = validate_records("sales_transactions", records)
        assert result["duplicate_count"] == 0
        assert result["valid_count"] == 100


# ---------------------------------------------------------------------------
# Timestamp handling tests
# ---------------------------------------------------------------------------

class TestTimestampHandling:

    def test_utc_timestamp_parseable(self):
        """All timestamps use UTC ISO 8601 format."""
        ts = "2025-06-15T14:30:00Z"
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 6

    def test_naive_timestamp_fails(self):
        """Timestamps without timezone should be flagged."""
        ts = "2025-06-15T14:30:00"
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is None, "Naive timestamp has no timezone info"
