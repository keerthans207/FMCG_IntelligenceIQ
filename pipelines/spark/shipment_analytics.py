#!/usr/bin/env python3
"""
Spark Job 5: Shipment Analytics

Calculates:
- Average delivery duration
- Expected vs actual delivery time
- Confirmed shipment delays
- Pending shipment risks
- Supplier delivery performance
- Location-wise delivery performance

Writes to gold layer.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, TimestampType


def run_shipment_analytics(spark, hdfs_base: str):
    """Run shipment analytics."""

    shipment_schema = StructType([
        StructField("shipment_id", StringType(), False),
        StructField("origin_location_id", StringType(), False),
        StructField("destination_location_id", StringType(), False),
        StructField("dispatch_timestamp", TimestampType(), False),
        StructField("expected_delivery_timestamp", TimestampType(), False),
        StructField("actual_delivery_timestamp", TimestampType(), True),
        StructField("shipment_status", StringType(), False),
    ])

    # Read raw shipments
    shipments = spark.read.schema(shipment_schema).json(f"{hdfs_base}/raw/shipments/")
    shipments.createOrReplaceTempView("shipments")

    # --- Shipment details with computed fields ---
    print("[1/5] Computing shipment delays...")
    shipment_details = spark.sql("""
        SELECT
            shipment_id,
            origin_location_id,
            destination_location_id,
            dispatch_timestamp,
            expected_delivery_timestamp,
            actual_delivery_timestamp,
            shipment_status,
            CASE
                WHEN actual_delivery_timestamp IS NOT NULL
                THEN BIGINT(actual_delivery_timestamp - dispatch_timestamp) / 3600
                ELSE NULL
            END AS delivery_duration_hours,
            CASE
                WHEN actual_delivery_timestamp IS NOT NULL
                THEN GREATEST(0, BIGINT(actual_delivery_timestamp - expected_delivery_timestamp) / 3600)
                ELSE 0
            END AS delay_hours,
            CASE
                WHEN actual_delivery_timestamp IS NOT NULL
                    AND actual_delivery_timestamp > expected_delivery_timestamp
                THEN true
                WHEN actual_delivery_timestamp IS NULL
                    AND shipment_status IN ('pending', 'in_transit')
                    AND expected_delivery_timestamp < CURRENT_TIMESTAMP()
                THEN true
                ELSE false
            END AS is_delayed
        FROM shipments
    """)
    shipment_details.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/shipment_analytics/shipment_details"
    )

    # --- Delivery statistics summary ---
    print("[2/5] Delivery statistics summary...")
    delivery_stats = spark.sql("""
        SELECT
            COUNT(*) AS total_shipments,
            SUM(CASE WHEN shipment_status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN shipment_status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count,
            SUM(CASE WHEN shipment_status = 'in_transit' THEN 1 ELSE 0 END) AS in_transit,
            SUM(CASE WHEN shipment_status = 'pending' THEN 1 ELSE 0 END) AS pending,
            ROUND(
                AVG(CASE
                    WHEN actual_delivery_timestamp IS NOT NULL
                    THEN BIGINT(actual_delivery_timestamp - dispatch_timestamp) / 3600.0
                END), 2
            ) AS avg_delivery_hours,
            ROUND(
                AVG(CASE
                    WHEN actual_delivery_timestamp IS NOT NULL
                    AND actual_delivery_timestamp > expected_delivery_timestamp
                    THEN BIGINT(actual_delivery_timestamp - expected_delivery_timestamp) / 3600.0
                END), 2
            ) AS avg_delay_hours
        FROM shipments
    """)
    delivery_stats.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/shipment_analytics/delivery_stats"
    )

    # --- Location-wise delivery performance ---
    print("[3/5] Location-wise delivery performance...")
    loc_performance = spark.sql("""
        SELECT
            destination_location_id,
            COUNT(*) AS total_shipments,
            SUM(CASE WHEN shipment_status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN shipment_status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count,
            ROUND(
                AVG(CASE
                    WHEN actual_delivery_timestamp IS NOT NULL
                    THEN BIGINT(actual_delivery_timestamp - dispatch_timestamp) / 3600.0
                END), 2
            ) AS avg_delivery_hours
        FROM shipments
        GROUP BY destination_location_id
        ORDER BY total_shipments DESC
    """)
    loc_performance.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/shipment_analytics/location_performance"
    )

    # --- Pending shipment risks (overdue or near-overdue) ---
    print("[4/5] Pending shipment risks...")
    pending_risks = spark.sql("""
        SELECT
            shipment_id,
            origin_location_id,
            destination_location_id,
            dispatch_timestamp,
            expected_delivery_timestamp,
            shipment_status,
            BIGINT(CURRENT_TIMESTAMP() - expected_delivery_timestamp) / 3600 AS overdue_hours
        FROM shipments
        WHERE actual_delivery_timestamp IS NULL
            AND shipment_status IN ('pending', 'in_transit')
            AND expected_delivery_timestamp < CURRENT_TIMESTAMP()
        ORDER BY overdue_hours DESC
    """)
    pending_risks.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/shipment_analytics/pending_risks"
    )

    # --- Confirmed delays detail ---
    print("[5/5] Confirmed delays detail...")
    confirmed_delays = spark.sql("""
        SELECT
            shipment_id,
            origin_location_id,
            destination_location_id,
            dispatch_timestamp,
            expected_delivery_timestamp,
            actual_delivery_timestamp,
            BIGINT(actual_delivery_timestamp - expected_delivery_timestamp) / 3600 AS delay_hours
        FROM shipments
        WHERE actual_delivery_timestamp IS NOT NULL
            AND actual_delivery_timestamp > expected_delivery_timestamp
        ORDER BY delay_hours DESC
    """)
    confirmed_delays.write.mode("overwrite").parquet(
        f"{hdfs_base}/gold/shipment_analytics/confirmed_delays"
    )

    print("Shipment analytics completed.")
    return {"tables_written": [
        "shipment_details", "delivery_stats", "location_performance",
        "pending_risks", "confirmed_delays"
    ]}


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-ShipmentAnalytics")
    hdfs_base = get_hdfs_base_path()
    try:
        run_shipment_analytics(spark, hdfs_base)
    except Exception as e:
        print(f"Shipment analytics FAILED: {e}")
        raise
    finally:
        spark.stop()
