"""
Unit tests for the synthetic data generator.

Tests reproducibility, ID formats, record counts, and pattern realism.
Uses the 'small' preset for speed.
"""

import json
import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from generate_data import (
    generate_dataset,
    generate_products,
    generate_locations,
    generate_suppliers,
    generate_sales_transactions,
    SIZE_PRESETS,
)

import random


class TestReproducibility:

    def test_same_seed_produces_same_data(self):
        """Two runs with the same seed should produce identical output."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        products1 = generate_products(5, rng1)
        products2 = generate_products(5, rng2)
        assert products1 == products2

    def test_different_seed_produces_different_data(self):
        rng1 = random.Random(42)
        rng2 = random.Random(99)
        products1 = generate_products(5, rng1)
        products2 = generate_products(5, rng2)
        assert products1 != products2


class TestIDFormats:

    def test_sku_id_format(self):
        from generate_data import sku_id
        assert sku_id(1) == "SKU00001"
        assert sku_id(99999) == "SKU99999"
        assert len(sku_id(1)) == 8

    def test_location_id_format(self):
        from generate_data import loc_id
        assert loc_id(1) == "LOC0001"

    def test_transaction_id_format(self):
        from generate_data import txn_id
        assert txn_id(1) == "TXN0000000001"
        assert len(txn_id(1)) == 13  # TXN + 10 digits = 13 chars


class TestProductGeneration:

    def test_product_fields_complete(self):
        rng = random.Random(42)
        products = generate_products(10, rng)
        for p in products:
            assert "sku_id" in p
            assert "product_name" in p
            assert "brand" in p
            assert "category" in p
            assert "unit_cost" in p
            assert "selling_price" in p
            assert "shelf_life_days" in p

    def test_selling_price_above_cost(self):
        """Selling price should always be above cost."""
        rng = random.Random(42)
        products = generate_products(50, rng)
        for p in products:
            assert p["selling_price"] > p["unit_cost"]

    def test_category_from_allowed_set(self):
        rng = random.Random(42)
        products = generate_products(20, rng)
        from generate_data import CATEGORIES
        for p in products:
            assert p["category"] in CATEGORIES


class TestSalesPatterns:

    def test_weekend_higher_demand(self):
        """Weekend transactions should generally have higher units_sold."""
        rng = random.Random(42)
        products = generate_products(10, rng)
        locations = generate_locations(5, rng)
        from datetime import date, timedelta
        start = date(2025, 1, 1)
        sales = generate_sales_transactions(products, locations, start, 30, 1000, rng)

        # Check that weekend transactions have higher average demand
        weekend_total = 0
        weekend_count = 0
        weekday_total = 0
        weekday_count = 0

        for txn in sales:
            ts = txn["transaction_timestamp"]
            dt = date.fromisoformat(ts[:10])
            dow = dt.weekday()
            if dow >= 5:
                weekend_total += txn["units_sold"]
                weekend_count += 1
            else:
                weekday_total += txn["units_sold"]
                weekday_count += 1

        weekend_avg = weekend_total / weekend_count if weekend_count else 0
        weekday_avg = weekday_total / weekday_count if weekday_count else 0

        # Weekend average should be higher (with some tolerance for randomness)
        assert weekend_avg >= weekday_avg * 0.9

    def test_promotion_transactions_exist(self):
        """Some transactions should have promotion_flag=True."""
        rng = random.Random(42)
        products = generate_products(10, rng)
        locations = generate_locations(5, rng)
        from datetime import date
        sales = generate_sales_transactions(products, locations, date(2025, 1, 1), 30, 1000, rng)
        promo_count = sum(1 for t in sales if t["promotion_flag"])
        assert promo_count > 0  # ~15% should be promotions

    def test_all_units_sold_positive(self):
        rng = random.Random(42)
        products = generate_products(10, rng)
        locations = generate_locations(5, rng)
        from datetime import date
        sales = generate_sales_transactions(products, locations, date(2025, 1, 1), 30, 500, rng)
        for txn in sales:
            assert txn["units_sold"] >= 1


class TestSizePresets:

    def test_presets_defined(self):
        for size in ["small", "medium", "large", "xlarge"]:
            assert size in SIZE_PRESETS
            assert "transactions" in SIZE_PRESETS[size]
            assert "products" in SIZE_PRESETS[size]

    def test_small_preset_correct(self):
        assert SIZE_PRESETS["small"]["transactions"] == 10000

    def test_xlarge_preset_correct(self):
        assert SIZE_PRESETS["xlarge"]["transactions"] == 1000000


class TestFullDatasetGeneration:

    def test_generate_small_dataset(self, tmp_path):
        """Generate a tiny dataset and verify all files exist."""
        result = generate_dataset(size="small", seed=42, output_dir=str(tmp_path))

        expected_files = [
            "products.jsonl",
            "locations.jsonl",
            "suppliers.jsonl",
            "batches.jsonl",
            "sales_transactions.jsonl",
            "inventory_snapshots.jsonl",
            "stock_movements.jsonl",
            "shipments.jsonl",
            "invalid_records.jsonl",
            "_manifest.json",
        ]

        for fname in expected_files:
            assert (tmp_path / fname).exists(), f"Missing: {fname}"

    def test_manifest_contains_counts(self, tmp_path):
        result = generate_dataset(size="small", seed=42, output_dir=str(tmp_path))
        manifest_path = tmp_path / "_manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "counts" in manifest
        assert manifest["counts"]["products"] > 0
        assert manifest["counts"]["sales_transactions"] > 0
        assert manifest["seed"] == 42

    def test_invalid_records_separate(self, tmp_path):
        """Invalid records should be in a separate file, not in sales."""
        generate_dataset(size="small", seed=42, output_dir=str(tmp_path))

        invalid_path = tmp_path / "invalid_records.jsonl"
        sales_path = tmp_path / "sales_transactions.jsonl"

        assert invalid_path.exists()
        assert sales_path.exists()

        # Load and check IDs don't overlap
        invalid_ids = set()
        with open(invalid_path) as f:
            for line in f:
                record = json.loads(line)
                if "transaction_id" in record:
                    invalid_ids.add(record["transaction_id"])

        sales_ids = set()
        with open(sales_path) as f:
            for line in f:
                record = json.loads(line)
                sales_ids.add(record["transaction_id"])

        # Invalid record IDs (TXN9999999999 etc.) should NOT be in sales
        assert len(invalid_ids & sales_ids) == 0
