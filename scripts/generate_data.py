#!/usr/bin/env python3
"""
FMCG SupplyChainIQ — Synthetic Data Generator

Generates a deterministic, reproducible FMCG dataset with realistic
patterns: product-specific demand, location-specific demand, weekday/
weekend variation, promotions, seasonality, supplier lead-time variation,
batch expiry differences, stockout events, delayed shipments, and
controlled inventory anomalies.

Invalid test records are kept SEPARATE from normal business records.

Usage:
    python scripts/generate_data.py --size small --output data/generated
    python scripts/generate_data.py --size medium --seed 42 --output data/generated

Sizes: small (10K), medium (100K), large (500K), xlarge (1M) transactions.
Default size: small.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Beverages", "Snacks", "Dairy", "Personal Care", "Household",
    "Bakery", "Confectionery", "Frozen Foods", "Health", "Baby Care",
]

BRANDS = [
    "FreshMart", "UrbanBite", "NatureNest", "PrimeChoice", "DailyDelight",
    "GreenHarvest", "QuickCrave", "WellnessPro", "HomeBasics", "LittleJoy",
    "PureLiving", "SnackTime", "AquaFresh", "GoodMorning", "CarePlus",
]

CITIES = [
    ("Mumbai", "Maharashtra", "West"),
    ("Delhi", "Delhi", "North"),
    ("Bangalore", "Karnataka", "South"),
    ("Chennai", "Tamil Nadu", "South"),
    ("Kolkata", "West Bengal", "East"),
    ("Hyderabad", "Telangana", "South"),
    ("Pune", "Maharashtra", "West"),
    ("Ahmedabad", "Gujarat", "West"),
    ("Jaipur", "Rajasthan", "North"),
    ("Lucknow", "Uttar Pradesh", "North"),
    ("Patna", "Bihar", "East"),
    ("Bhopal", "Madhya Pradesh", "Central"),
    ("Chandigarh", "Punjab", "North"),
    ("Kochi", "Kerala", "South"),
    ("Indore", "Madhya Pradesh", "Central"),
]

UNIT_SIZES = ["100g", "200g", "250g", "500g", "1kg", "500ml", "1L", "2L", "250ml", "100ml"]

SIZE_PRESETS = {
    "small":  {"transactions": 10000,  "products": 50,  "locations": 10, "suppliers": 8,  "days": 90},
    "medium": {"transactions": 100000, "products": 100, "locations": 20, "suppliers": 15, "days": 180},
    "large":  {"transactions": 500000, "products": 200, "locations": 30, "suppliers": 20, "days": 365},
    "xlarge": {"transactions": 1000000,"products": 300, "locations": 40, "suppliers": 25, "days": 365},
}


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

def sku_id(n: int) -> str:
    return f"SKU{n:05d}"

def loc_id(n: int) -> str:
    return f"LOC{n:04d}"

def sup_id(n: int) -> str:
    return f"SUP{n:04d}"

def bat_id(n: int) -> str:
    return f"BAT{n:06d}"

def txn_id(n: int) -> str:
    return f"TXN{n:010d}"

def snp_id(n: int) -> str:
    return f"SNP{n:010d}"

def mov_id(n: int) -> str:
    return f"MOV{n:010d}"

def shp_id(n: int) -> str:
    return f"SHP{n:08d}"


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_products(n_products: int, rng: random.Random) -> list[dict[str, Any]]:
    """Generate product master records with category-specific shelf life."""
    products: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    shelf_life_by_category = {
        "Dairy": 14, "Bakery": 10, "Frozen Foods": 180, "Snacks": 180,
        "Confectionery": 270, "Beverages": 365, "Personal Care": 730,
        "Household": 730, "Health": 540, "Baby Care": 540,
    }

    for i in range(1, n_products + 1):
        cat = rng.choice(CATEGORIES)
        brand = rng.choice(BRANDS)
        # Product-specific base demand multiplier (0.5 to 2.5)
        base_demand = round(rng.uniform(0.5, 2.5), 2)
        unit_cost = round(rng.uniform(5.0, 150.0), 2)
        # Selling price is 20-60% above cost
        margin = rng.uniform(0.2, 0.6)
        selling_price = round(unit_cost * (1 + margin), 2)

        products.append({
            "sku_id": sku_id(i),
            "product_name": f"{brand} {cat} {i}",
            "brand": brand,
            "category": cat,
            "unit_size": rng.choice(UNIT_SIZES),
            "unit_cost": unit_cost,
            "selling_price": selling_price,
            "shelf_life_days": shelf_life_by_category.get(cat, 180),
            "created_at": (now - timedelta(days=rng.randint(30, 400))).isoformat(),
            # Internal metadata (not part of schema, used by generator)
            "_base_demand": base_demand,
        })
    return products


def generate_locations(n_locations: int, rng: random.Random) -> list[dict[str, Any]]:
    """Generate warehouse and retail locations across Indian cities."""
    locations: list[dict[str, Any]] = []
    n_warehouses = max(2, n_locations // 4)

    for i in range(1, n_locations + 1):
        city, state, region = rng.choice(CITIES)
        if i <= n_warehouses:
            loc_type = "warehouse"
        elif i <= n_warehouses + n_warehouses:
            loc_type = "distributor"
        else:
            loc_type = "retail"

        # Location-specific demand multiplier (0.5 to 2.0)
        loc_demand = round(rng.uniform(0.5, 2.0), 2)

        locations.append({
            "location_id": loc_id(i),
            "location_name": f"{city} {loc_type.capitalize()}",
            "location_type": loc_type,
            "city": city,
            "state": state,
            "region": region,
            "_base_demand": loc_demand,
        })
    return locations


def generate_suppliers(n_suppliers: int, rng: random.Random) -> list[dict[str, Any]]:
    """Generate suppliers with varying lead times."""
    suppliers: list[dict[str, Any]] = []
    for i in range(1, n_suppliers + 1):
        _, _, region = rng.choice(CITIES)
        suppliers.append({
            "supplier_id": sup_id(i),
            "supplier_name": f"Supplier {i}",
            "region": region,
            "typical_lead_time_days": rng.randint(3, 21),
        })
    return suppliers


def generate_batches(
    products: list[dict[str, Any]],
    suppliers: list[dict[str, Any]],
    start_date: date,
    days: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Generate product batches with manufacturing and expiry dates."""
    batches: list[dict[str, Any]] = []
    batch_counter = 0

    for product in products:
        shelf_life = product["shelf_life_days"]
        # 2-5 batches per product spread over the period
        n_batches = rng.randint(2, 5)
        for _ in range(n_batches):
            batch_counter += 1
            mfg_offset = rng.randint(0, max(1, days - 30))
            mfg_date = start_date + timedelta(days=mfg_offset)
            exp_date = mfg_date + timedelta(days=shelf_life)
            supplier = rng.choice(suppliers)

            batches.append({
                "batch_id": bat_id(batch_counter),
                "sku_id": product["sku_id"],
                "manufacturing_date": mfg_date.isoformat(),
                "expiry_date": exp_date.isoformat(),
                "initial_quantity": rng.randint(500, 5000),
                "supplier_id": supplier["supplier_id"],
            })

    return batches


def generate_sales_transactions(
    products: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    start_date: date,
    days: int,
    n_transactions: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """
    Generate sales transactions with realistic patterns:
    - Product-specific demand (base_demand multiplier)
    - Location-specific demand
    - Weekday vs weekend variation (weekend higher)
    - Monthly seasonality (festive season Oct-Dec higher)
    - Promotions (random, ~15% of transactions)
    """
    transactions: list[dict[str, Any]] = []
    retail_locs = [l for l in locations if l["location_type"] == "retail"]

    if not retail_locs:
        retail_locs = locations  # fallback if all are warehouses

    # Seasonal multiplier by month (festive season boost)
    seasonal = {1: 0.8, 2: 0.75, 3: 0.85, 4: 0.9, 5: 0.95, 6: 1.0,
                7: 0.9, 8: 0.95, 9: 1.1, 10: 1.3, 11: 1.4, 12: 1.5}

    for i in range(1, n_transactions + 1):
        # Pick day
        day_offset = rng.randint(0, days - 1)
        txn_date = start_date + timedelta(days=day_offset)

        # Pick product and location
        product = rng.choice(products)
        location = rng.choice(retail_locs)

        # Base demand for this product/location combination
        base = product.get("_base_demand", 1.0) * location.get("_base_demand", 1.0)

        # Day-of-week effect: weekend 30-50% higher
        dow = txn_date.weekday()
        if dow >= 5:  # Saturday, Sunday
            day_mult = rng.uniform(1.3, 1.5)
        elif dow == 0:  # Monday slightly lower
            day_mult = rng.uniform(0.8, 0.95)
        else:
            day_mult = rng.uniform(0.9, 1.1)

        # Seasonal effect
        season_mult = seasonal.get(txn_date.month, 1.0)

        # Promotion (15% chance)
        is_promo = rng.random() < 0.15
        promo_mult = rng.uniform(1.2, 1.8) if is_promo else 1.0

        # Final units sold
        base_units = int(base * 10 * day_mult * season_mult * promo_mult)
        units_sold = max(1, base_units + rng.randint(-3, 3))

        # Transaction timestamp (business hours: 8:00-22:00)
        hour = rng.randint(8, 21)
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        txn_timestamp = datetime(
            txn_date.year, txn_date.month, txn_date.day,
            hour, minute, second, tzinfo=timezone.utc
        )

        # Price (promotions may discount)
        if is_promo:
            unit_price = round(product["selling_price"] * rng.uniform(0.75, 0.90), 2)
        else:
            unit_price = product["selling_price"]

        transactions.append({
            "transaction_id": txn_id(i),
            "transaction_timestamp": txn_timestamp.isoformat(),
            "sku_id": product["sku_id"],
            "store_id": location["location_id"],
            "units_sold": units_sold,
            "unit_price": unit_price,
            "promotion_flag": is_promo,
        })

    # Sort by timestamp
    transactions.sort(key=lambda t: t["transaction_timestamp"])
    return transactions


def generate_inventory_snapshots(
    products: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    sales: list[dict[str, Any]],
    start_date: date,
    days: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """
    Generate daily inventory snapshots for each SKU/location/batch combo.

    A snapshot is a point-in-time observation, NOT a complete transaction
    history. Current stock is derived from the latest snapshot.
    """
    snapshots: list[dict[str, Any]] = []
    snap_counter = 0

    # Group batches by sku
    batches_by_sku: dict[str, list[dict[str, Any]]] = {}
    for batch in batches:
        batches_by_sku.setdefault(batch["sku_id"], []).append(batch)

    # Aggregate daily sales by sku + location
    daily_sales: dict[str, dict[str, int]] = {}  # f"{sku}_{loc}" -> {date_str: total}
    for txn in sales:
        key = f"{txn['sku_id']}_{txn['store_id']}"
        day_str = txn["transaction_timestamp"][:10]
        daily_sales.setdefault(key, {})
        daily_sales[key][day_str] = daily_sales[key].get(day_str, 0) + txn["units_sold"]

    # Only generate snapshots for retail/warehouse locations
    inv_locations = [l for l in locations if l["location_type"] in ("warehouse", "retail", "distributor")]

    # Sample to keep snapshot count manageable
    snapshot_combos: list[tuple[dict, dict, dict]] = []
    for loc in inv_locations:
        for product in products:
            sku_batches = batches_by_sku.get(product["sku_id"], [])
            if not sku_batches:
                continue
            # 1-2 batches per sku/location
            chosen = rng.sample(sku_batches, min(2, len(sku_batches)))
            for batch in chosen:
                snapshot_combos.append((product, loc, batch))

    # Limit total combos for large datasets
    max_combos = min(len(snapshot_combos), 5000 if days <= 90 else 10000)
    if len(snapshot_combos) > max_combos:
        snapshot_combos = rng.sample(snapshot_combos, max_combos)

    # Generate daily snapshots
    for product, loc, batch in snapshot_combos:
        current_qty = batch["initial_quantity"]
        key = f"{product['sku_id']}_{loc['location_id']}"

        # Take snapshots every N days (daily is too many for large datasets)
        snap_interval = 7 if days <= 180 else 14
        for day_offset in range(0, days, snap_interval):
            snap_date = start_date + timedelta(days=day_offset)
            snap_counter += 1

            # Subtract sales since last snapshot
            for d in range(day_offset - snap_interval + 1, day_offset + 1):
                if d < 0:
                    continue
                d_str = (start_date + timedelta(days=d)).isoformat()
                sold = daily_sales.get(key, {}).get(d_str, 0)
                current_qty = max(0, current_qty - sold)

            # Small random adjustment (restocking)
            if day_offset > 0 and rng.random() < 0.3:
                restock = rng.randint(50, 500)
                current_qty += restock

            # Reserved quantity (10-30% of on hand)
            reserved = int(current_qty * rng.uniform(0.05, 0.15))

            snap_timestamp = datetime(
                snap_date.year, snap_date.month, snap_date.day,
                0, 0, 0, tzinfo=timezone.utc
            )

            snapshots.append({
                "snapshot_id": snp_id(snap_counter),
                "snapshot_timestamp": snap_timestamp.isoformat(),
                "location_id": loc["location_id"],
                "sku_id": product["sku_id"],
                "batch_id": batch["batch_id"],
                "on_hand_quantity": current_qty,
                "reserved_quantity": reserved,
            })

    return snapshots


def generate_stock_movements(
    products: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
    start_date: date,
    days: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Generate stock movement events linked to shipments and adjustments."""
    movements: list[dict[str, Any]] = []
    mov_counter = 0

    # Inbound movements from shipments
    for shipment in shipments:
        if shipment["shipment_status"] in ("delivered", "in_transit"):
            mov_counter += 1
            ts = shipment["dispatch_timestamp"]
            # Pick a product and batch
            product = rng.choice(products)
            sku_batches = [b for b in batches if b["sku_id"] == product["sku_id"]]
            if not sku_batches:
                continue
            batch = rng.choice(sku_batches)

            movements.append({
                "movement_id": mov_id(mov_counter),
                "timestamp": ts,
                "location_id": shipment["destination_location_id"],
                "sku_id": product["sku_id"],
                "batch_id": batch["batch_id"],
                "movement_type": "inbound",
                "quantity_change": rng.randint(100, 1000),
                "reference_id": shipment["shipment_id"],
            })

    # Outbound movements (sales fulfillment)
    n_outbound = len(products) * len([l for l in locations if l["location_type"] in ("retail", "warehouse")]) * 2
    for _ in range(min(n_outbound, 5000)):
        mov_counter += 1
        product = rng.choice(products)
        sku_batches = [b for b in batches if b["sku_id"] == product["sku_id"]]
        if not sku_batches:
            continue
        batch = rng.choice(sku_batches)
        loc = rng.choice([l for l in locations if l["location_type"] != "warehouse"])
        day_offset = rng.randint(0, days - 1)
        ts_date = start_date + timedelta(days=day_offset)
        ts = datetime(ts_date.year, ts_date.month, ts_date.day,
                       rng.randint(8, 18), rng.randint(0, 59), tzinfo=timezone.utc)

        movements.append({
            "movement_id": mov_id(mov_counter),
            "timestamp": ts.isoformat(),
            "location_id": loc["location_id"],
            "sku_id": product["sku_id"],
            "batch_id": batch["batch_id"],
            "movement_type": "outbound",
            "quantity_change": -rng.randint(1, 50),
            "reference_id": f"SALES-{ts_date.isoformat()}",
        })

    # Controlled anomalies: a few adjustments and damage events
    n_anomalies = max(5, len(products) // 10)
    for _ in range(n_anomalies):
        mov_counter += 1
        product = rng.choice(products)
        sku_batches = [b for b in batches if b["sku_id"] == product["sku_id"]]
        if not sku_batches:
            continue
        batch = rng.choice(sku_batches)
        loc = rng.choice(locations)
        day_offset = rng.randint(0, days - 1)
        ts_date = start_date + timedelta(days=day_offset)
        ts = datetime(ts_date.year, ts_date.month, ts_date.day,
                       rng.randint(8, 18), tzinfo=timezone.utc)

        anomaly_type = rng.choice(["adjustment", "damage", "expiry_writeoff"])
        qty = rng.randint(-200, 200) if anomaly_type == "adjustment" else -rng.randint(10, 100)

        movements.append({
            "movement_id": mov_id(mov_counter),
            "timestamp": ts.isoformat(),
            "location_id": loc["location_id"],
            "sku_id": product["sku_id"],
            "batch_id": batch["batch_id"],
            "movement_type": anomaly_type,
            "quantity_change": qty,
            "reference_id": f"ADJ-{mov_counter}",
        })

    movements.sort(key=lambda m: m["timestamp"])
    return movements


def generate_shipments(
    locations: list[dict[str, Any]],
    products: list[dict[str, Any]],
    start_date: date,
    days: int,
    n_shipments: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """
    Generate shipment records between locations.

    Includes:
    - Realistic delivery times based on origin/destination region
    - ~15% delayed shipments (actual > expected)
    - Some pending/in-transit shipments
    """
    shipments: list[dict[str, Any]] = []
    warehouses = [l for l in locations if l["location_type"] == "warehouse"]
    distributors = [l for l in locations if l["location_type"] == "distributor"]
    retail = [l for l in locations if l["location_type"] == "retail"]

    # Origins: warehouses and distributors; Destinations: distributors and retail
    origins = warehouses + distributors if warehouses else locations
    destinations = distributors + retail if retail else locations

    if len(origins) < 2 or len(destinations) < 1:
        origins = locations
        destinations = locations

    now = datetime.now(timezone.utc)

    for i in range(1, n_shipments + 1):
        origin = rng.choice(origins)
        # Avoid same origin and destination
        dest_choices = [d for d in destinations if d["location_id"] != origin["location_id"]]
        if not dest_choices:
            dest_choices = destinations
        dest = rng.choice(dest_choices)

        # Dispatch time within business hours
        day_offset = rng.randint(0, days - 1)
        dispatch_date = start_date + timedelta(days=day_offset)
        dispatch_ts = datetime(
            dispatch_date.year, dispatch_date.month, dispatch_date.day,
            rng.randint(8, 17), rng.randint(0, 59), tzinfo=timezone.utc
        )

        # Expected delivery: 2-10 days depending on distance/region
        if origin["region"] == dest["region"]:
            expected_days = rng.randint(2, 5)
        else:
            expected_days = rng.randint(5, 10)
        expected_ts = dispatch_ts + timedelta(days=expected_days)

        # ~15% delayed, ~70% delivered on time, ~15% in transit/pending
        status_roll = rng.random()
        if dispatch_ts < now - timedelta(days=15):
            # Past shipment — should be delivered
            if status_roll < 0.15:
                # Delayed
                delay_hours = rng.randint(12, 96)
                actual_ts = expected_ts + timedelta(hours=delay_hours)
                status = "delayed"
            else:
                # On time (slight variation)
                variation = rng.randint(-12, 12)
                actual_ts = expected_ts + timedelta(hours=variation)
                status = "delivered"
        else:
            # Recent/future shipment
            if status_roll < 0.15:
                actual_ts = None
                status = "pending"
            elif status_roll < 0.30:
                actual_ts = None
                status = "in_transit"
            else:
                # Delivered
                variation = rng.randint(-12, 12)
                actual_ts = expected_ts + timedelta(hours=variation)
                status = "delivered"

        shipments.append({
            "shipment_id": shp_id(i),
            "origin_location_id": origin["location_id"],
            "destination_location_id": dest["location_id"],
            "dispatch_timestamp": dispatch_ts.isoformat(),
            "expected_delivery_timestamp": expected_ts.isoformat(),
            "actual_delivery_timestamp": actual_ts.isoformat() if actual_ts else None,
            "shipment_status": status,
        })

    shipments.sort(key=lambda s: s["dispatch_timestamp"])
    return shipments


def generate_invalid_records(
    products: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    """
    Generate deliberately INVALID records for testing rejection logic.
    These are kept SEPARATE from normal business records.
    """
    invalid: list[dict[str, Any]] = []

    # Missing required field
    invalid.append({
        "transaction_id": "TXN9999999999",
        "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
        "sku_id": products[0]["sku_id"],
        # Missing store_id, units_sold, unit_price, promotion_flag
    })

    # Invalid SKU format
    invalid.append({
        "transaction_id": "TXN9999999998",
        "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
        "sku_id": "INVALID_SKU",
        "store_id": locations[0]["location_id"],
        "units_sold": 5,
        "unit_price": 10.0,
        "promotion_flag": False,
    })

    # Negative units_sold
    invalid.append({
        "transaction_id": "TXN9999999997",
        "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
        "sku_id": products[0]["sku_id"],
        "store_id": locations[0]["location_id"],
        "units_sold": -10,
        "unit_price": 10.0,
        "promotion_flag": False,
    })

    # Duplicate transaction_id
    invalid.append({
        "transaction_id": "TXN9999999999",  # Same as first invalid record
        "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
        "sku_id": products[0]["sku_id"],
        "store_id": locations[0]["location_id"],
        "units_sold": 3,
        "unit_price": 15.0,
        "promotion_flag": True,
    })

    return invalid


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_jsonl(filepath: Path, records: list[dict[str, Any]]) -> int:
    """Write records as JSON Lines. Returns count written."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for record in records:
            # Strip internal metadata fields (prefixed with _)
            clean = {k: v for k, v in record.items() if not k.startswith("_")}
            f.write(json.dumps(clean, default=str) + "\n")
    return len(records)


def write_manifest(output_dir: Path, stats: dict[str, Any]) -> None:
    """Write a generation manifest with counts and parameters."""
    manifest_path = output_dir / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_dataset(
    size: str = "small",
    seed: int = 42,
    output_dir: str = "data/generated",
) -> dict[str, Any]:
    """
    Generate a complete FMCG dataset.

    Parameters
    ----------
    size : str — small, medium, large, xlarge
    seed : int — random seed for reproducibility
    output_dir : str — output directory path

    Returns
    -------
    dict with counts and file paths
    """
    rng = random.Random(seed)
    preset = SIZE_PRESETS.get(size, SIZE_PRESETS["small"])

    n_products = preset["products"]
    n_locations = preset["locations"]
    n_suppliers = preset["suppliers"]
    n_transactions = preset["transactions"]
    days = preset["days"]

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    print(f"Generating {size} dataset ({n_transactions:,} transactions, seed={seed})...")

    # Generate all entities
    products = generate_products(n_products, rng)
    locations = generate_locations(n_locations, rng)
    suppliers = generate_suppliers(n_suppliers, rng)
    batches = generate_batches(products, suppliers, start_date, days, rng)
    sales = generate_sales_transactions(products, locations, start_date, days, n_transactions, rng)

    # Number of shipments: roughly proportional to products * locations
    n_shipments = min(n_products * n_locations // 3, 20000)
    shipments = generate_shipments(locations, products, start_date, days, n_shipments, rng)

    inventory = generate_inventory_snapshots(products, locations, batches, sales, start_date, days, rng)
    movements = generate_stock_movements(products, locations, batches, shipments, start_date, days, rng)
    invalid = generate_invalid_records(products, locations, rng)

    # Write output files
    out = Path(output_dir)
    counts = {
        "products": write_jsonl(out / "products.jsonl", products),
        "locations": write_jsonl(out / "locations.jsonl", locations),
        "suppliers": write_jsonl(out / "suppliers.jsonl", suppliers),
        "batches": write_jsonl(out / "batches.jsonl", batches),
        "sales_transactions": write_jsonl(out / "sales_transactions.jsonl", sales),
        "inventory_snapshots": write_jsonl(out / "inventory_snapshots.jsonl", inventory),
        "stock_movements": write_jsonl(out / "stock_movements.jsonl", movements),
        "shipments": write_jsonl(out / "shipments.jsonl", shipments),
        "invalid_records": write_jsonl(out / "invalid_records.jsonl", invalid),
    }

    stats = {
        "size": size,
        "seed": seed,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": days,
        "counts": counts,
        "output_dir": str(out),
    }
    write_manifest(out, stats)

    print(f"\nDataset generation complete:")
    for name, count in counts.items():
        print(f"  {name:25s} {count:>10,} records")
    print(f"  Manifest written to: {out / '_manifest.json'}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="FMCG SupplyChainIQ Synthetic Data Generator")
    parser.add_argument("--size", choices=list(SIZE_PRESETS.keys()), default="small",
                        help="Dataset size preset (default: small)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output", default="data/generated",
                        help="Output directory (default: data/generated)")
    args = parser.parse_args()

    generate_dataset(size=args.size, seed=args.seed, output_dir=args.output)


if __name__ == "__main__":
    main()
