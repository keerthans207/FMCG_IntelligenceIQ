#!/usr/bin/env python3
"""
Spark Job 4: Expiry Analytics

Calculates:
- Days until expiry per batch
- Expired quantities
- Approaching-expiry quantities
- Expiry-risk classification
- Inventory exposure by batch
- FEFO (First Expired, First Out) dispatch recommendations

Writes to gold layer.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def run_expiry_analytics(spark, hdfs_base: str):
    """Run expiry analytics."""

    # Read silver tables
    inventory = spark.read.parquet(f"{hdfs_base}/silver/validated_inventory")
    batches_raw = spark.read.json(f"{hdfs_base}/raw/batches/")
    products = spark.read.parquet(f"{hdfs_base}/silver/validated_products")

    inventory.createOrReplaceTempView("inventory")
    batches_raw.createOrReplaceTempView("batches")
    products.createOrReplaceTempView("products")

    # --- Latest stock per batch ---
    print("[1/5] Latest stock per batch...")
    latest_stock = spark.sql("""
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY location_id, sku_id, batch_id
                    ORDER BY snapshot_timestamp DESC
                ) AS rn
            FROM inventory
        )
        SELECT location_id, sku_id, batch_id, available_stock
        FROM ranked WHERE rn = 1
    """)
    latest_stock.createOrReplaceTempView("latest_stock")

    # --- Days until expiry + risk classification ---
    print("[2/5] Days until expiry and risk classification...")
    expiry_analysis = spark.sql("""
        SELECT
            ls.location_id,
            ls.sku_id,
            ls.batch_id,
            p.product_name,
            b.expiry_date,
            DATEDIFF(b.expiry_date, CURRENT_DATE()) AS days_until_expiry,
            ls.available_stock,
            CASE
                WHEN DATEDIFF(b.expiry_date, CURRENT_DATE()) <= 0 THEN 'expired'
                WHEN DATEDIFF(b.expiry_date, CURRENT_DATE()) <= 7 THEN 'critical'
                WHEN DATEDIFF(b.expiry_date, CURRENT_DATE()) <= 30 THEN 'approaching'
                ELSE 'healthy'
            END AS expiry_risk
        FROM latest_stock ls
        JOIN batches b ON ls.batch_id = b.batch_id
        LEFT JOIN products p ON ls.sku_id = p.sku_id
    """)
    expiry_analysis.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/expiry_analytics/expiry_analysis"
    )

    # --- Expired quantities ---
    print("[3/5] Expired quantities summary...")
    expired_summary = expiry_analysis.filter("expiry_risk = 'expired'").groupBy(
        "location_id", "sku_id", "product_name"
    ).agg(
        F.sum("available_stock").alias("expired_quantity"),
        F.count("batch_id").alias("expired_batch_count"),
    )
    expired_summary.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/expiry_analytics/expired_summary"
    )

    # --- Expiry exposure by risk level ---
    print("[4/5] Expiry exposure summary...")
    exposure_summary = expiry_analysis.groupBy("expiry_risk").agg(
        F.count("*").alias("batch_count"),
        F.sum("available_stock").alias("total_quantity"),
        F.countDistinct("sku_id").alias("affected_skus"),
    )
    exposure_summary.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/expiry_analytics/exposure_summary"
    )

    # --- FEFO dispatch recommendations ---
    print("[5/5] FEFO dispatch recommendations...")
    fefo_ranked = expiry_analysis.withColumn(
        "fefo_rank",
        F.row_number().over(
            Window.partitionBy("location_id", "sku_id")
            .orderBy(F.col("expiry_date").asc())
        )
    )
    fefo_recommendations = fefo_ranked.select(
        "location_id", "sku_id", "product_name", "batch_id",
        "expiry_date", "days_until_expiry", "available_stock",
        "expiry_risk", "fefo_rank",
    ).orderBy("location_id", "sku_id", "fefo_rank")
    fefo_recommendations.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/expiry_analytics/fefo_recommendations"
    )

    print("Expiry analytics completed.")
    return {"tables_written": [
        "expiry_analysis", "expired_summary", "exposure_summary",
        "fefo_recommendations"
    ]}


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-ExpiryAnalytics")
    hdfs_base = get_hdfs_base_path()
    try:
        run_expiry_analytics(spark, hdfs_base)
    except Exception as e:
        print(f"Expiry analytics FAILED: {e}")
        raise
    finally:
        spark.stop()
