"""
Integration tests for MongoDB operations.

These tests require a running MongoDB instance. They are marked with
@pytest.mark.integration and will be SKIPPED if MongoDB is not available.

Run locally with:  python -m pytest tests/integration/ -m integration -v
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fmcg.config.settings import EnvSettings


def _mongo_available() -> bool:
    """Check if MongoDB is reachable."""
    try:
        from fmcg.database.init_db import health_check
        result = health_check()
        return result["status"] == "healthy"
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mongo_settings():
    return EnvSettings()


class TestMongoConnection:

    @pytest.mark.skipif(not _mongo_available(), reason="MongoDB not available")
    def test_health_check(self, mongo_settings):
        from fmcg.database.init_db import health_check
        result = health_check(mongo_settings)
        assert result["status"] == "healthy"

    @pytest.mark.skipif(not _mongo_available(), reason="MongoDB not available")
    def test_database_initialization(self, mongo_settings):
        from fmcg.database.init_db import init_database
        result = init_database(mongo_settings)
        assert "products" in result["collections"]
        assert "sales_transactions" in result["collections"]


class TestMongoWrite:

    @pytest.mark.skipif(not _mongo_available(), reason="MongoDB not available")
    def test_idempotent_upsert(self, mongo_settings):
        """Re-writing the same record should not create duplicates."""
        from fmcg.ingestion.mongo_writer import bulk_upsert

        test_record = {
            "sku_id": "SKU99999",
            "product_name": "Test Product",
            "brand": "TestBrand",
            "category": "Snacks",
            "unit_size": "100g",
            "unit_cost": 10.0,
            "selling_price": 20.0,
            "shelf_life_days": 180,
            "created_at": "2025-01-01T00:00:00Z",
        }

        # Write once
        result1 = bulk_upsert("products", [test_record], settings=mongo_settings)
        assert result1["errors"] == 0

        # Write again — should match, not create duplicate
        result2 = bulk_upsert("products", [test_record], settings=mongo_settings)
        assert result2["matched"] >= 1
        assert result2["upserted"] == 0  # already exists

    @pytest.mark.skipif(not _mongo_available(), reason="MongoDB not available")
    def test_bulk_upsert_multiple(self, mongo_settings):
        from fmcg.ingestion.mongo_writer import bulk_upsert

        records = [
            {"sku_id": f"SKU{i:05d}", "product_name": f"Test {i}",
             "brand": "Test", "category": "Snacks", "unit_size": "100g",
             "unit_cost": 5.0, "selling_price": 10.0, "shelf_life_days": 180,
             "created_at": "2025-01-01T00:00:00Z"}
            for i in range(900, 910)
        ]

        result = bulk_upsert("products", records, settings=mongo_settings)
        assert result["errors"] == 0
        assert result["total"] == 10
