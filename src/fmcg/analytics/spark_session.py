"""
Spark session factory for FMCG SupplyChainIQ.

Creates and configures a SparkSession for the pipeline jobs.
Supports both YARN (production) and local[*] (unit testing) modes.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from pyspark.sql import SparkSession
except ImportError:
    SparkSession = None  # type: ignore[assignment,misc]


def create_spark_session(
    app_name: str = "FMCG-SupplyChainIQ",
    master: str | None = None,
    config_overrides: dict | None = None,
) -> "SparkSession":
    """
    Create a configured SparkSession.

    Parameters
    ----------
    app_name : str — Spark application name
    master : str — Spark master URL. Defaults to env SPARK_MASTER or "local[*]"
    config_overrides : dict — additional Spark conf overrides

    Notes
    -----
    When running on YARN, ensures Hadoop config and JARs are on the classpath.
    When running locally, uses local[*] for unit testing.
    """
    if SparkSession is None:
        raise ImportError(
            "PySpark is not installed. Install requirements on the remote server. "
            "This module is not available for local execution on Windows."
        )

    spark_master = master or os.environ.get("SPARK_MASTER", "local[*]")

    builder = SparkSession.builder.appName(app_name)

    # Core Spark configuration
    builder = builder.master(spark_master)

    # Spark SQL settings
    builder = builder.config("spark.sql.shuffle.partitions",
                             os.environ.get("SPARK_SQL_SHUFFLE_PARTITIONS", "32"))
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")

    # I/O settings
    builder = builder.config("spark.sql.parquet.compression.codec", "snappy")

    # Memory (env-configurable, defaults are conservative for academic EC2)
    if spark_master.startswith("yarn"):
        builder = builder.config("spark.driver.memory",
                                 os.environ.get("SPARK_DRIVER_MEMORY", "2g"))
        builder = builder.config("spark.executor.memory",
                                 os.environ.get("SPARK_EXECUTOR_MEMORY", "2g"))
        builder = builder.config("spark.executor.cores",
                                 os.environ.get("SPARK_EXECUTOR_CORES", "2"))
        builder = builder.config("spark.executor.instances",
                                 os.environ.get("SPARK_NUM_EXECUTORS", "2"))
        builder = builder.config("spark.yarn.queue",
                                 os.environ.get("SPARK_YARN_QUEUE", "default"))

    # Python settings
    builder = builder.config("spark.sql.execution.pyspark.enabled", "true")

    # Apply overrides
    if config_overrides:
        for key, value in config_overrides.items():
            builder = builder.config(key, value)

    return builder.getOrCreate()


def get_hdfs_base_path() -> str:
    """Return the HDFS base path from environment or config."""
    host = os.environ.get("HDFS_NAMENODE_HOST", "localhost")
    port = os.environ.get("HDFS_NAMENODE_PORT", "9000")
    root = os.environ.get("HDFS_ROOT_PATH", "/fmcg-supplychainiq")
    return f"hdfs://{host}:{port}{root}"
