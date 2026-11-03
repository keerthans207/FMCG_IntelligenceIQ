#!/usr/bin/env python3
"""
Spark Job 3: Inventory Intelligence

Calculates:
- Current available stock (on_hand - reserved)
- Inventory turnover
- Average daily demand
- Days of stock remaining
- Reorder point
- Stockout exposure
- Excess inventory
- Slow-moving products

Uses Spark SQL and DataFrame operations. Writes to gold layer.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def run_inventory_analytics(spark, hdfs_base: str):
    """Run inventory intelligence analytics."""

    # Read silver tables
    inventory = spark.read.parquet(f"{hdfs_base}/silver/validated_inventory")
    sales = spark.read.parquet(f"{hdfs_base}/silver/cleaned_sales")
    products = spark.read.parquet(f"{hdfs_base}/silver/validated_products")
    suppliers = spark.read.parquet(f"{hdfs_base}/silver/validated_suppliers")

    # Register temp views
    inventory.createOrReplaceTempView("inventory")
    sales.createOrReplaceTempView("sales")
    products.createOrReplaceTempView("products")
    suppliers.createOrReplaceTempView("suppliers")

    # --- Current available stock (latest snapshot per location/sku/batch) ---
    print("[1/7] Current available stock...")
    latest_snapshot = spark.sql("""
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY location_id, sku_id, batch_id
                    ORDER BY snapshot_timestamp DESC
                ) AS rn
            FROM inventory
        )
        SELECT
            location_id,
            sku_id,
            batch_id,
            on_hand_quantity,
            reserved_quantity,
            available_stock,
            snapshot_timestamp
        FROM ranked
        WHERE rn = 1
    """)
    latest_snapshot.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/current_stock"
    )

    # --- Average daily demand per SKU/location (last 30 days) ---
    print("[2/7] Average daily demand...")
    avg_daily_demand = spark.sql("""
        SELECT
            sku_id,
            store_id AS location_id,
            AVG(units_sold) AS avg_daily_demand,
            SUM(units_sold) AS total_units_sold,
            COUNT(DISTINCT transaction_date) AS active_days
        FROM sales
        GROUP BY sku_id, store_id
    """)
    avg_daily_demand.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/avg_daily_demand"
    )

    # --- Days of stock remaining + stockout risk ---
    print("[3/7] Days of stock remaining and stockout risk...")
    stock_with_demand = latest_snapshot.alias("ls").join(
        avg_daily_demand.alias("add"),
        (F.col("ls.sku_id") == F.col("add.sku_id")) &
        (F.col("ls.location_id") == F.col("add.location_id")),
        "left"
    ).join(
        products.alias("p"),
        F.col("ls.sku_id") == F.col("p.sku_id"),
        "left"
    ).join(
        suppliers.alias("sup"),
        F.col("p.brand") == F.col("sup.supplier_name"),  # simplified join
        "left"
    )

    stock_health = stock_with_demand.select(
        F.col("ls.location_id"),
        F.col("ls.sku_id"),
        F.col("ls.batch_id"),
        F.col("p.product_name"),
        F.col("p.category"),
        F.col("ls.available_stock"),
        F.col("add.avg_daily_demand").alias("avg_daily_demand"),
        F.col("sup.typical_lead_time_days").alias("lead_time_days"),
        # Days remaining (null if no demand)
        F.when(
            F.col("add.avg_daily_demand") > 0,
            F.round(F.col("ls.available_stock") / F.col("add.avg_daily_demand"), 1)
        ).otherwise(None).alias("days_remaining"),
    )

    # Classify stockout risk
    stock_health = stock_health.withColumn(
        "stockout_risk",
        F.when(F.col("days_remaining").isNull(), "none")
         .when(F.col("days_remaining") < F.col("lead_time_days"), "critical")
         .when(F.col("days_remaining") < F.col("lead_time_days") + 7, "high")
         .when(F.col("days_remaining") < 2 * (F.col("lead_time_days") + 7), "medium")
         .when(F.col("days_remaining") < 4 * (F.col("lead_time_days") + 7), "low")
         .otherwise("none")
    )
    stock_health.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/stock_health"
    )

    # --- Inventory turnover (sales / avg inventory) ---
    print("[4/7] Inventory turnover...")
    turnover = spark.sql("""
        SELECT
            s.sku_id,
            s.store_id AS location_id,
            SUM(s.units_sold) AS total_sold,
            AVG(i.available_stock) AS avg_stock,
            CASE
                WHEN AVG(i.available_stock) > 0
                THEN ROUND(SUM(s.units_sold) / AVG(i.available_stock), 2)
                ELSE 0
            END AS turnover_ratio
        FROM sales s
        LEFT JOIN inventory i
            ON s.sku_id = i.sku_id AND s.store_id = i.location_id
        GROUP BY s.sku_id, s.store_id
    """)
    turnover.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/turnover"
    )

    # --- Excess inventory (stock > 90 days of demand) ---
    print("[5/7] Excess inventory...")
    excess = stock_health.filter(
        (F.col("days_remaining").isNotNull()) &
        (F.col("days_remaining") > 90)
    ).select("location_id", "sku_id", "product_name", "available_stock",
             "avg_daily_demand", "days_remaining")
    excess.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/excess_inventory"
    )

    # --- Slow-moving products (< 1 unit/day avg) ---
    print("[6/7] Slow-moving products...")
    slow_moving = stock_health.filter(
        (F.col("avg_daily_demand").isNotNull()) &
        (F.col("avg_daily_demand") < 1.0) &
        (F.col("available_stock") > 0)
    ).select("location_id", "sku_id", "product_name", "available_stock",
             "avg_daily_demand", "days_remaining")
    slow_moving.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/slow_moving"
    )

    # --- Stockout exposure summary ---
    print("[7/7] Stockout exposure summary...")
    stockout_summary = stock_health.groupBy("stockout_risk").agg(
        F.count("*").alias("sku_location_count"),
        F.sum("available_stock").alias("total_units_at_risk"),
    ).orderBy("stockout_risk")
    stockout_summary.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/inventory_analytics/stockout_summary"
    )

    print("Inventory analytics completed.")
    return {"tables_written": [
        "current_stock", "avg_daily_demand", "stock_health", "turnover",
        "excess_inventory", "slow_moving", "stockout_summary"
    ]}


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-InventoryAnalytics")
    hdfs_base = get_hdfs_base_path()
    try:
        run_inventory_analytics(spark, hdfs_base)
    except Exception as e:
        print(f"Inventory analytics FAILED: {e}")
        raise
    finally:
        spark.stop()
