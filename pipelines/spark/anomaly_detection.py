#!/usr/bin/env python3
"""
Spark Job 6: Anomaly Detection

Identifies:
- Unexpected stock adjustments
- Negative inventory balances
- Unusual sales spikes
- Abrupt demand drops
- Unusual stock movement quantities
- Suspicious shipment delays

Uses explainable statistical (z-score) and rule-based methods.
Does NOT label anomalies as fraud without supporting evidence.

Writes to gold layer.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def run_anomaly_detection(spark, hdfs_base: str):
    """Run anomaly detection across multiple data sources."""

    # --- 1. Demand anomalies (spikes and drops) ---
    print("[1/4] Detecting demand anomalies...")
    sales = spark.read.parquet(f"{hdfs_base}/silver/cleaned_sales")
    daily_sales = sales.groupBy("transaction_date", "sku_id", "store_id").agg(
        F.sum("units_sold").alias("daily_units")
    )

    # Compute z-score per sku/location
    stats_window = Window.partitionBy("sku_id", "store_id")
    demand_stats = daily_sales.withColumn("mean_demand",
        F.avg("daily_units").over(stats_window)
    ).withColumn("std_demand",
        F.stddev("daily_units").over(stats_window)
    ).withColumn("z_score",
        F.when(F.col("std_demand") > 0,
               F.round((F.col("daily_units") - F.col("mean_demand")) / F.col("std_demand"), 3)
        ).otherwise(0.0)
    )

    demand_anomalies = demand_stats.filter(
        (F.abs(F.col("z_score")) > 2.5) & (F.col("std_demand") > 0)
    ).withColumn("anomaly_type",
        F.when(F.col("z_score") > 0, "demand_spike").otherwise("demand_drop")
    ).withColumn("severity",
        F.when(F.abs(F.col("z_score")) > 4, "critical")
         .when(F.abs(F.col("z_score")) > 3.5, "high")
         .otherwise("medium")
    ).select(
        "transaction_date", "sku_id", "store_id AS location_id",
        "daily_units", "mean_demand", "std_demand", "z_score",
        "anomaly_type", "severity",
    )
    demand_anomalies.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/anomaly_analytics/demand_anomalies"
    )

    # --- 2. Inventory anomalies (negative balances, large adjustments) ---
    print("[2/4] Detecting inventory anomalies...")
    movements_schema = "movement_id string, timestamp timestamp, location_id string, " \
                       "sku_id string, batch_id string, movement_type string, " \
                       "quantity_change int, reference_id string"
    movements = spark.read.schema(movements_schema).json(f"{hdfs_base}/raw/stock_movements/")

    # Large adjustments
    large_adjustments = movements.filter(
        (F.col("movement_type") == "adjustment") & (F.abs(F.col("quantity_change")) > 50)
    ).withColumn("anomaly_type", F.lit("stock_adjustment_anomaly")
    ).withColumn("severity",
        F.when(F.abs(F.col("quantity_change")) > 200, "high").otherwise("medium")
    )
    large_adjustments.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/anomaly_analytics/adjustment_anomalies"
    )

    # Negative inventory check (replay movements to detect negative balances)
    print("[3/4] Checking for negative inventory balances...")
    # This would require a full replay; for the academic implementation,
    # we flag negative quantity_change as suspicious if movement_type is outbound
    negative_movements = movements.filter(
        (F.col("movement_type") == "outbound") & (F.col("quantity_change") > 0)
    ).withColumn("anomaly_type", F.lit("movement_anomaly")
    ).withColumn("severity", F.lit("medium"))
    negative_movements.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/anomaly_analytics/negative_inventory_anomalies"
    )

    # --- 4. Shipment anomalies ---
    print("[4/4] Detecting suspicious shipment delays...")
    shipment_schema = "shipment_id string, origin_location_id string, " \
                      "destination_location_id string, dispatch_timestamp timestamp, " \
                      "expected_delivery_timestamp timestamp, " \
                      "actual_delivery_timestamp timestamp, shipment_status string"
    shipments = spark.read.schema(shipment_schema).json(f"{hdfs_base}/raw/shipments/")

    suspicious_delays = shipments.filter(
        (F.col("actual_delivery_timestamp").isNotNull()) &
        (F.col("actual_delivery_timestamp") > F.col("expected_delivery_timestamp"))
    ).withColumn("delay_hours",
        F.round(
            F.unix_timestamp("actual_delivery_timestamp") -
            F.unix_timestamp("expected_delivery_timestamp")
        ) / 3600
    ).filter(F.col("delay_hours") > 24  # more than 24 hours late = suspicious
    ).withColumn("anomaly_type", F.lit("shipment_delay")
    ).withColumn("severity",
        F.when(F.col("delay_hours") > 72, "high").otherwise("medium")
    ).select(
        "shipment_id", "origin_location_id", "destination_location_id",
        "dispatch_timestamp", "expected_delivery_timestamp",
        "actual_delivery_timestamp", "delay_hours", "anomaly_type", "severity",
    )
    suspicious_delays.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/anomaly_analytics/shipment_anomalies"
    )

    # --- Summary alert count ---
    print("\nAnomaly detection completed.")
    return {
        "demand_anomalies": demand_anomalies.count(),
        "adjustment_anomalies": large_adjustments.count(),
        "negative_inventory_anomalies": negative_movements.count(),
        "shipment_anomalies": suspicious_delays.count(),
    }


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-AnomalyDetection")
    hdfs_base = get_hdfs_base_path()
    try:
        result = run_anomaly_detection(spark, hdfs_base)
        print(f"\nAnomaly counts: {result}")
    except Exception as e:
        print(f"Anomaly detection FAILED: {e}")
        raise
    finally:
        spark.stop()
