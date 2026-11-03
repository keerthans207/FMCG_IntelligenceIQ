"""
Integration tests for Spark operations.

These tests require a running Spark + HDFS instance. They are marked
with @pytest.mark.integration and will be SKIPPED if Spark is not available.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


def _spark_available() -> bool:
    """Check if PySpark can be imported and a session created."""
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.master("local[1]").appName("test").getOrCreate()
        spark.stop()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not _spark_available(), reason="PySpark not available")
class TestSparkDataFrames:

    def test_create_dataframe(self):
        from pyspark.sql import SparkSession
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType

        spark = SparkSession.builder.master("local[1]").appName("test").getOrCreate()
        try:
            schema = StructType([
                StructField("name", StringType(), False),
                StructField("age", IntegerType(), False),
            ])
            data = [("Alice", 30), ("Bob", 25)]
            df = spark.createDataFrame(data, schema)
            assert df.count() == 2
            assert "name" in df.columns
        finally:
            spark.stop()

    def test_spark_sql(self):
        from pyspark.sql import SparkSession
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType

        spark = SparkSession.builder.master("local[1]").appName("test").getOrCreate()
        try:
            schema = StructType([
                StructField("category", StringType(), False),
                StructField("units", IntegerType(), False),
            ])
            data = [("Snacks", 10), ("Snacks", 20), ("Dairy", 5)]
            df = spark.createDataFrame(data, schema)
            df.createOrReplaceTempView("sales")

            result = spark.sql("SELECT category, SUM(units) as total FROM sales GROUP BY category ORDER BY total DESC")
            rows = result.collect()
            assert rows[0]["category"] == "Snacks"
            assert rows[0]["total"] == 30
        finally:
            spark.stop()
