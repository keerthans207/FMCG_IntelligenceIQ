# FMCG SupplyChainIQ — Data Dictionary

This document defines every collection, field, data type, constraint, and
relationship used across MongoDB (operational), HDFS (historical data lake),
and Spark (processing).

All timestamps are stored in **UTC** (ISO 8601 format).

---

## Collection / Dataset Overview

| Collection | Primary DB | HDFS Layer | Format | Unique Key |
|---|---|---|---|---|
| products | MongoDB | raw, bronze | JSONL / Parquet | sku_id |
| locations | MongoDB | raw | JSONL / Parquet | location_id |
| suppliers | MongoDB | raw | JSONL / Parquet | supplier_id |
| batches | MongoDB | raw, bronze | JSONL / Parquet | batch_id |
| sales_transactions | MongoDB | raw, bronze, silver | JSONL / Parquet | transaction_id |
| inventory_snapshots | MongoDB | raw, bronze, silver | JSONL / Parquet | snapshot_id |
| stock_movements | MongoDB | raw, bronze, silver | JSONL / Parquet | movement_id |
| shipments | MongoDB | raw, bronze, silver | JSONL / Parquet | shipment_id |
| analytics_alerts | MongoDB | gold (copy) | Document | alert_id |
| forecasts | MongoDB | forecasts/predictions | Document | forecast_id |
| pipeline_runs | MongoDB | metadata | Document | run_id |

---

## 1. products

| Field | Type | Constraint | Description |
|---|---|---|---|
| sku_id | string | `^SKU[0-9]{5}$`, unique | Stock-keeping unit identifier |
| product_name | string | 1–200 chars | Human-readable product name |
| brand | string | not empty | Brand name |
| category | string | enum (10 categories) | Product category |
| unit_size | string | — | e.g. "200g", "1L", "500ml" |
| unit_cost | double | ≥ 0 | Cost per unit (supplier price) |
| selling_price | double | ≥ 0 | Retail selling price per unit |
| shelf_life_days | int | ≥ 1 | Total shelf life from manufacturing |
| created_at | date | UTC | Record creation timestamp |

Categories: Beverages, Snacks, Dairy, Personal Care, Household, Bakery,
Confectionery, Frozen Foods, Health, Baby Care.

---

## 2. locations

| Field | Type | Constraint | Description |
|---|---|---|---|
| location_id | string | `^LOC[0-9]{4}$`, unique | Location identifier |
| location_name | string | not empty | Warehouse or store name |
| location_type | string | enum | warehouse, distributor, wholesale, retail |
| city | string | — | City |
| state | string | — | State |
| region | string | enum | North, South, East, West, Central |

---

## 3. suppliers

| Field | Type | Constraint | Description |
|---|---|---|---|
| supplier_id | string | `^SUP[0-9]{4}$`, unique | Supplier identifier |
| supplier_name | string | not empty | Supplier company name |
| region | string | enum | North, South, East, West, Central |
| typical_lead_time_days | int | 1–60 | Average days from order to delivery |

---

## 4. batches

| Field | Type | Constraint | Description |
|---|---|---|---|
| batch_id | string | `^BAT[0-9]{6}$`, unique | Batch identifier |
| sku_id | string | FK → products | Product this batch belongs to |
| manufacturing_date | date | ISO date | Date of manufacture |
| expiry_date | date | ISO date, > manufacturing_date | Expiry date |
| initial_quantity | int | ≥ 0 | Initial units in batch |
| supplier_id | string | FK → suppliers | Supplier who provided this batch |

**Derived field (calculated at query time, not stored):**
- `days_until_expiry = expiry_date - current_date`

---

## 5. sales_transactions

| Field | Type | Constraint | Description |
|---|---|---|---|
| transaction_id | string | `^TXN[0-9]{10}$`, unique | Transaction identifier |
| transaction_timestamp | datetime | UTC | When the sale occurred |
| sku_id | string | FK → products | Product sold |
| store_id | string | FK → locations (retail) | Store where sale occurred |
| units_sold | int | ≥ 1 | Units sold in this transaction |
| unit_price | double | ≥ 0 | Price per unit at time of sale |
| promotion_flag | boolean | — | True if a promotion was active |

**Derived fields (Spark SQL):**
- `transaction_date` = DATE(transaction_timestamp)
- `total_amount` = units_sold * unit_price

---

## 6. inventory_snapshots

| Field | Type | Constraint | Description |
|---|---|---|---|
| snapshot_id | string | `^SNP[0-9]{10}$`, unique | Snapshot identifier |
| snapshot_timestamp | datetime | UTC | When the snapshot was taken |
| location_id | string | FK → locations | Location of stock |
| sku_id | string | FK → products | Product |
| batch_id | string | FK → batches | Specific batch |
| on_hand_quantity | int | ≥ 0 | Physical units present |
| reserved_quantity | int | ≥ 0 | Units reserved for orders |

**Calculated (not stored directly):**
- `available_stock = on_hand_quantity - reserved_quantity`

> A snapshot is a point-in-time observation, NOT a complete transaction
> history. Current stock is derived by taking the latest snapshot per
> location/sku/batch and summing, or by replaying stock movements.
> Snapshots and movements are kept logically separate.

---

## 7. stock_movements

| Field | Type | Constraint | Description |
|---|---|---|---|
| movement_id | string | `^MOV[0-9]{10}$`, unique | Movement event identifier |
| timestamp | datetime | UTC | When the movement occurred |
| location_id | string | FK → locations | Affected location |
| sku_id | string | FK → products | Affected product |
| batch_id | string | FK → batches | Affected batch |
| movement_type | string | enum | inbound, outbound, transfer_in, transfer_out, adjustment, damage, expiry_writeoff |
| quantity_change | int | + or − | Positive for inbound/transfer_in, negative for outbound |
| reference_id | string | — | Links to shipment, transaction, or adjustment reason |

---

## 8. shipments

| Field | Type | Constraint | Description |
|---|---|---|---|
| shipment_id | string | `^SHP[0-9]{8}$`, unique | Shipment identifier |
| origin_location_id | string | FK → locations | Source location |
| destination_location_id | string | FK → locations | Destination |
| dispatch_timestamp | datetime | UTC | When shipped |
| expected_delivery_timestamp | datetime | UTC | Expected delivery |
| actual_delivery_timestamp | datetime, nullable | UTC | Null until delivered |
| shipment_status | string | enum | pending, in_transit, delivered, delayed, cancelled |

**Derived fields:**
- `delivery_duration_hours` = actual_delivery - dispatch (when delivered)
- `delay_hours` = max(0, actual_delivery - expected_delivery) (when delivered)
- `is_delayed` = delay_hours > 0

---

## 9. analytics_alerts

| Field | Type | Constraint | Description |
|---|---|---|---|
| alert_id | string | unique | Generated alert identifier |
| alert_type | string | enum | Type of alert (see below) |
| severity | string | enum | low, medium, high, critical |
| sku_id | string, nullable | — | Related SKU (if applicable) |
| location_id | string, nullable | — | Related location |
| batch_id | string, nullable | — | Related batch |
| alert_description | string | — | Human-readable explanation |
| recommendation | string | — | Suggested action |
| created_at | datetime | UTC | Alert creation time |
| acknowledged | boolean | — | Whether acknowledged by operator |

Alert types: stockout_risk, expiry_risk, excess_inventory, slow_moving,
shipment_delay, negative_inventory, demand_spike, demand_drop,
stock_adjustment_anomaly, movement_anomaly.

---

## 10. forecasts

| Field | Type | Constraint | Description |
|---|---|---|---|
| forecast_id | string | unique | Forecast record identifier |
| sku_id | string | — | Product forecasted |
| location_id | string | — | Location forecasted |
| forecast_date | date | ISO date | Date being forecasted |
| predicted_units | double | ≥ 0 | Predicted units sold |
| model_version | string | — | Model identifier (e.g. "rf-v1") |
| created_at | datetime | UTC | When forecast was generated |

---

## 11. pipeline_runs

| Field | Type | Constraint | Description |
|---|---|---|---|
| run_id | string | unique | Pipeline execution identifier |
| start_time | datetime | UTC | Pipeline start |
| end_time | datetime, nullable | UTC | Pipeline end (null if running) |
| status | string | enum | running, completed, failed, partial |
| records_ingested | int | — | Records written to MongoDB |
| records_processed | int | — | Records processed by Spark |
| records_rejected | int | — | Records that failed validation |
| execution_duration | double | seconds | Total execution time |
| error_message | string, nullable | — | Error details if failed |

---

## HDFS Data Lake Layers

| Layer | Purpose | Format | Example |
|---|---|---|---|
| raw | Verbatim copy of source records | JSONL | raw/sales/ |
| bronze | Raw loaded into Spark, minimal type coercion | Parquet | bronze/sales/ |
| silver | Cleaned, validated, deduplicated | Parquet | silver/cleaned_sales/ |
| gold | Aggregated analytics ready for consumption | Parquet | gold/demand_analytics/ |
| forecasts | ML training data, predictions, evaluation | Parquet | forecasts/predictions/ |
| metadata | Schemas, manifests, run logs | JSON/Parquet | metadata/pipeline_runs/ |

---

## Schema Evolution

- New optional fields may be added without breaking existing records.
- Field removal requires a documented migration step.
- Timestamps always use UTC ISO 8601.
- Duplicate detection uses the unique business identifier (e.g. transaction_id),
  not the MongoDB `_id`.
- Idempotent writes use `update_one(..., upsert=True)` with the unique key as filter.

---

## Timestamp Handling

- All datetime fields stored in UTC.
- Generation timestamps reference a fixed `GENERATOR_SEED` for reproducibility.
- Sales `transaction_timestamp` spans the configured `days` window ending at
  generation time.
- Inventory snapshots are taken daily at 00:00 UTC.
- Shipment dispatch timestamps fall within business hours (08:00–18:00 UTC).

---

## Duplicate Management

- Each collection has a unique business key with a unique index.
- Ingestion uses `upsert` (update-or-insert) keyed on the business identifier.
- Re-running the pipeline with the same input does NOT create duplicates.
- The pipeline records `records_rejected` to track duplicates/invalid records.
