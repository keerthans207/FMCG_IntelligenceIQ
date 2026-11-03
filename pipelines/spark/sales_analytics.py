#!/usr/bin/env python3
"""
Spark Job 2: Sales Analytics

Calculates daily/weekly/monthly sales, product-wise, category-wise,
location-wise sales, sales trends, and promotion-related demand changes.

Uses Spark SQL. Writes results to the gold layer (Parquet).
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F


def run_sales_analytics(spark, hdfs_base: str):
    """Run sales analytics and write gold outputs."""

    # Read silver tables
    sales = spark.read.parquet(f"{hdfs_base}/silver/cleaned_sales")
    products = spark.read.parquet(f"{hdfs_base}/silver/validated_products")
    locations = spark.read.parquet(f"{hdfs_base}/silver/validated_locations")

    # Register temp views for Spark SQL
    sales.createOrReplaceTempView("sales")
    products.createOrReplaceTempView("products")
    locations.createOrReplaceTempView("locations")

    # --- Daily sales ---
    print("[1/5] Daily sales...")
    daily_sales = spark.sql("""
        SELECT
            transaction_date,
            sku_id,
            store_id,
            SUM(units_sold) AS total_units,
            SUM(total_amount) AS total_revenue,
            COUNT(*) AS transaction_count
        FROM sales
        GROUP BY transaction_date, sku_id, store_id
    """)
    daily_sales.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/daily_sales")

    # --- Weekly sales ---
    print("[2/5] Weekly sales...")
    weekly_sales = spark.sql("""
        SELECT
            YEAR(transaction_date) AS year,
            weekofyear(transaction_date) AS week,
            sku_id,
            SUM(units_sold) AS total_units,
            SUM(total_amount) AS total_revenue
        FROM sales
        GROUP BY YEAR(transaction_date), weekofyear(transaction_date), sku_id
    """)
    weekly_sales.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/weekly_sales")

    # --- Monthly sales ---
    print("[3/5] Monthly sales...")
    monthly_sales = spark.sql("""
        SELECT
            YEAR(transaction_date) AS year,
            MONTH(transaction_date) AS month,
            sku_id,
            SUM(units_sold) AS total_units,
            SUM(total_amount) AS total_revenue
        FROM sales
        GROUP BY YEAR(transaction_date), MONTH(transaction_date), sku_id
    """)
    monthly_sales.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/monthly_sales")

    # --- Category-wise sales ---
    print("[4/5] Category-wise sales...")
    category_sales = spark.sql("""
        SELECT
            p.category,
            YEAR(s.transaction_date) AS year,
            MONTH(s.transaction_date) AS month,
            SUM(s.units_sold) AS total_units,
            SUM(s.total_amount) AS total_revenue
        FROM sales s
        JOIN products p ON s.sku_id = p.sku_id
        GROUP BY p.category, YEAR(s.transaction_date), MONTH(s.transaction_date)
    """)
    category_sales.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/category_sales")

    # --- Promotion impact ---
    print("[5/5] Promotion impact analysis...")
    promo_impact = spark.sql("""
        SELECT
            sku_id,
            promotion_flag,
            AVG(units_sold) AS avg_units,
            AVG(unit_price) AS avg_price,
            COUNT(*) AS transaction_count,
            SUM(units_sold) AS total_units
        FROM sales
        GROUP BY sku_id, promotion_flag
        ORDER BY sku_id, promotion_flag
    """)
    promo_impact.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/promotion_impact")

    # --- Top-selling products (query 1 from spec) ---
    top_products = spark.sql("""
        SELECT
            s.sku_id,
            p.product_name,
            p.category,
            SUM(s.units_sold) AS total_units_sold,
            SUM(s.total_amount) AS total_revenue
        FROM sales s
        JOIN products p ON s.sku_id = p.sku_id
        GROUP BY s.sku_id, p.product_name, p.category
        ORDER BY total_units_sold DESC
    """)
    top_products.write.mode("overwrite").parquet(f"{hdfs_base}/gold/demand_analytics/top_products")

    print("Sales analytics completed.")
    return {"tables_written": ["daily_sales", "weekly_sales", "monthly_sales",
                                "category_sales", "promotion_impact", "top_products"]}


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-SalesAnalytics")
    hdfs_base = get_hdfs_base_path()
    try:
        run_sales_analytics(spark, hdfs_base)
    except Exception as e:
        print(f"Sales analytics FAILED: {e}")
        raise
    finally:
        spark.stop()
