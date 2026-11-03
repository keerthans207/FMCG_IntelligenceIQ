#!/usr/bin/env python3
"""
Spark Job 1: Data Ingestion and Validation

Reads source datasets from HDFS raw layer, validates schemas, handles
missing values, detects duplicates, standardizes data types, validates
foreign-key relationships, generates data-quality statistics, and writes
validated datasets to the silver layer (Parquet).

Usage (remote):
    spark-submit --master yarn pipelines/spark/ingest.py
    spark-submit --master local[2] pipelines/spark/ingest.py
"""

from __future__ import annotations

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path


def run_ingest(spark, hdfs_base: str):
    """
    Run the ingestion and validation job.

    Reads raw JSONL → validates → writes silver Parquet.
    Returns a dict of quality statistics.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType,
        IntegerType, TimestampType, BooleanType, DateType,
    )

    stats: dict = {}

    # --- Define schemas for raw data ---

    products_schema = StructType([
        StructField("sku_id", StringType(), False),
        StructField("product_name", StringType(), False),
        StructField("brand", StringType(), True),
        StructField("category", StringType(), False),
        StructField("unit_size", StringType(), True),
        StructField("unit_cost", DoubleType(), False),
        StructField("selling_price", DoubleType(), False),
        StructField("shelf_life_days", IntegerType(), False),
        StructField("created_at", TimestampType(), True),
    ])

    locations_schema = StructType([
        StructField("location_id", StringType(), False),
        StructField("location_name", StringType(), False),
        StructField("location_type", StringType(), False),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("region", StringType(), True),
    ])

    sales_schema = StructType([
        StructField("transaction_id", StringType(), False),
        StructField("transaction_timestamp", TimestampType(), False),
        StructField("sku_id", StringType(), False),
        StructField("store_id", StringType(), False),
        StructField("units_sold", IntegerType(), False),
        StructField("unit_price", DoubleType(), False),
        StructField("promotion_flag", BooleanType(), True),
    ])

    inventory_schema = StructType([
        StructField("snapshot_id", StringType(), False),
        StructField("snapshot_timestamp", TimestampType(), False),
        StructField("location_id", StringType(), False),
        StructField("sku_id", StringType(), False),
        StructField("batch_id", StringType(), False),
        StructField("on_hand_quantity", IntegerType(), False),
        StructField("reserved_quantity", IntegerType(), False),
    ])

    # --- Process each dataset ---

    # Products
    print("[1/4] Processing products...")
    products = spark.read.schema(products_schema).json(f"{hdfs_base}/raw/products/")
    products_total = products.count()
    # Deduplicate by sku_id (keep first)
    products_clean = products.dropDuplicates(["sku_id"])
    # Validate: drop records with null critical fields
    products_clean = products_clean.filter(
        F.col("sku_id").isNotNull() &
        F.col("product_name").isNotNull() &
        F.col("category").isNotNull() &
        (F.col("unit_cost") >= 0) &
        (F.col("selling_price") >= 0)
    )
    products_clean.write.mode("overwrite").parquet(f"{hdfs_base}/silver/validated_products")
    products_valid = products_clean.count()
    stats["products"] = {"total": products_total, "valid": products_valid,
                         "rejected": products_total - products_valid}

    # Locations
    print("[2/4] Processing locations...")
    locations = spark.read.schema(locations_schema).json(f"{hdfs_base}/raw/locations/")
    locations_total = locations.count()
    locations_clean = locations.dropDuplicates(["location_id"]).filter(
        F.col("location_id").isNotNull() & F.col("location_name").isNotNull()
    )
    locations_clean.write.mode("overwrite").parquet(f"{hdfs_base}/silver/validated_locations")
    locations_valid = locations_clean.count()
    stats["locations"] = {"total": locations_total, "valid": locations_valid,
                          "rejected": locations_total - locations_valid}

    # Sales — with FK validation against products
    print("[3/4] Processing sales transactions...")
    sales = spark.read.schema(sales_schema).json(f"{hdfs_base}/raw/sales/")
    sales_total = sales.count()

    # Deduplicate by transaction_id
    sales_clean = sales.dropDuplicates(["transaction_id"])

    # Validate: positive units_sold, non-null required fields
    sales_clean = sales_clean.filter(
        F.col("transaction_id").isNotNull() &
        F.col("sku_id").isNotNull() &
        F.col("store_id").isNotNull() &
        (F.col("units_sold") >= 1) &
        (F.col("unit_price") >= 0)
    )

    # FK validation: sku_id must exist in products
    sales_clean = sales_clean.join(
        products_clean.select("sku_id").distinct(),
        on="sku_id",
        how="inner",
    )

    # Add derived columns
    sales_clean = sales_clean.withColumn(
        "transaction_date", F.to_date(F.col("transaction_timestamp"))
    ).withColumn(
        "total_amount", F.col("units_sold") * F.col("unit_price")
    )

    sales_clean.write.mode("overwrite").partitionBy("transaction_date").parquet(
        f"{hdfs_base}/silver/cleaned_sales"
    )
    sales_valid = sales_clean.count()
    stats["sales"] = {"total": sales_total, "valid": sales_valid,
                      "rejected": sales_total - sales_valid}

    # Inventory snapshots
    print("[4/4] Processing inventory snapshots...")
    inventory = spark.read.schema(inventory_schema).json(f"{hdfs_base}/raw/inventory/")
    inventory_total = inventory.count()
    inventory_clean = inventory.dropDuplicates(["snapshot_id"]).filter(
        F.col("snapshot_id").isNotNull() &
        F.col("location_id").isNotNull() &
        F.col("sku_id").isNotNull() &
        (F.col("on_hand_quantity") >= 0) &
        (F.col("reserved_quantity") >= 0)
    )
    inventory_clean = inventory_clean.withColumn(
        "snapshot_date", F.to_date(F.col("snapshot_timestamp"))
    ).withColumn(
        "available_stock", F.col("on_hand_quantity") - F.col("reserved_quantity")
    )
    inventory_clean.write.mode("overwrite").partitionBy("snapshot_date").parquet(
        f"{hdfs_base}/silver/validated_inventory"
    )
    inventory_valid = inventory_clean.count()
    stats["inventory"] = {"total": inventory_total, "valid": inventory_valid,
                          "rejected": inventory_total - inventory_valid}

    # Print summary
    print("\n=== Ingestion & Validation Summary ===")
    for ds, s in stats.items():
        print(f"  {ds:15s}  total={s['total']:>10,}  valid={s['valid']:>10,}  rejected={s['rejected']:>5}")

    return stats


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-Ingest")
    hdfs_base = get_hdfs_base_path()
    print(f"HDFS base: {hdfs_base}")

    try:
        stats = run_ingest(spark, hdfs_base)
        print("\nIngestion job completed successfully.")
    except Exception as e:
        print(f"\nIngestion job FAILED: {e}")
        raise
    finally:
        spark.stop()
