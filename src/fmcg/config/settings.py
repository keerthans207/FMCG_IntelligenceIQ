"""
Configuration loader.

Reads environment variables and YAML config files, merging them into
a single validated configuration object. All connection strings, paths,
and tunable parameters flow through here so nothing is hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Environment-driven settings (loaded from .env or shell environment)
# ---------------------------------------------------------------------------

class EnvSettings(BaseSettings):
    """Settings pulled from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    # MongoDB
    mongo_host: str = Field(default="localhost", alias="MONGO_HOST")
    mongo_port: int = Field(default=27017, alias="MONGO_PORT")
    mongo_user: str = Field(default="", alias="MONGO_USER")
    mongo_password: str = Field(default="", alias="MONGO_PASSWORD")
    mongo_auth_source: str = Field(default="admin", alias="MONGO_AUTH_SOURCE")
    mongo_db_name: str = Field(default="fmcg_supplychainiq", alias="MONGO_DB_NAME")
    mongo_uri: str = Field(default="", alias="MONGO_URI")

    # HDFS
    hdfs_namenode_host: str = Field(default="localhost", alias="HDFS_NAMENODE_HOST")
    hdfs_namenode_port: int = Field(default=9000, alias="HDFS_NAMENODE_PORT")
    hdfs_webui_port: int = Field(default=9870, alias="HDFS_WEBUI_PORT")
    hdfs_root_path: str = Field(default="/fmcg-supplychainiq", alias="HDFS_ROOT_PATH")
    hdfs_user: str = Field(default="fmcg", alias="HDFS_USER")

    # Spark
    spark_master: str = Field(default="yarn", alias="SPARK_MASTER")
    spark_deploy_mode: str = Field(default="client", alias="SPARK_DEPLOY_MODE")
    spark_driver_memory: str = Field(default="2g", alias="SPARK_DRIVER_MEMORY")
    spark_executor_memory: str = Field(default="2g", alias="SPARK_EXECUTOR_MEMORY")
    spark_executor_cores: int = Field(default=2, alias="SPARK_EXECUTOR_CORES")
    spark_num_executors: int = Field(default=2, alias="SPARK_NUM_EXECUTORS")
    spark_yarn_queue: str = Field(default="default", alias="SPARK_YARN_QUEUE")

    # File system paths (remote)
    data_dir: str = Field(default="/data/fmcg", alias="DATA_DIR")
    mongodb_data_dir: str = Field(default="/data/mongodb", alias="MONGODB_DATA_DIR")
    hadoop_namenode_dir: str = Field(default="/data/hadoop/namenode", alias="HADOOP_NAMENODE_DIR")
    hadoop_datanode_dir: str = Field(default="/data/hadoop/datanode", alias="HADOOP_DATANODE_DIR")
    spark_tmp_dir: str = Field(default="/data/spark/tmp", alias="SPARK_TMP_DIR")
    model_dir: str = Field(default="/data/fmcg/models", alias="MODEL_DIR")
    log_dir: str = Field(default="/data/fmcg/logs", alias="LOG_DIR")

    # Data generation
    generator_seed: int = Field(default=42, alias="GENERATOR_SEED")
    generator_size: str = Field(default="small", alias="GENERATOR_SIZE")
    generator_output_dir: str = Field(default="data/generated", alias="GENERATOR_OUTPUT_DIR")

    # FastAPI
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=2, alias="API_WORKERS")

    # Streamlit
    dashboard_port: int = Field(default=8501, alias="DASHBOARD_PORT")

    # Pipeline
    pipeline_checkpoint_dir: str = Field(default="/data/fmcg/checkpoints", alias="PIPELINE_CHECKPOINT_DIR")
    pipeline_fail_fast: bool = Field(default=False, alias="PIPELINE_FAIL_FAST")

    def mongo_connection_uri(self) -> str:
        """Build a MongoDB connection URI from individual fields, or use MONGO_URI."""
        if self.mongo_uri:
            return self.mongo_uri
        auth = ""
        if self.mongo_user and self.mongo_password:
            auth = f"{self.mongo_user}:{self.mongo_password}@"
        return f"mongodb://{auth}{self.mongo_host}:{self.mongo_port}"

    def hdfs_uri(self) -> str:
        """Build the HDFS NameNode URI."""
        return f"hdfs://{self.hdfs_namenode_host}:{self.hdfs_namenode_port}"


# ---------------------------------------------------------------------------
# YAML config loader
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "configs"


def _load_yaml(filename: str) -> dict[str, Any]:
    path = _CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class AppConfig:
    """Merged application configuration: env settings + YAML overrides."""

    env: EnvSettings = field(default_factory=EnvSettings)
    app_yaml: dict[str, Any] = field(default_factory=dict)
    remote_yaml: dict[str, Any] = field(default_factory=dict)
    hadoop_yaml: dict[str, Any] = field(default_factory=dict)
    spark_yaml: dict[str, Any] = field(default_factory=dict)
    mongodb_yaml: dict[str, Any] = field(default_factory=dict)
    pipeline_yaml: dict[str, Any] = field(default_factory=dict)

    @property
    def mongo_db_name(self) -> str:
        return self.env.mongo_db_name

    @property
    def hdfs_root(self) -> str:
        return self.env.hdfs_root_path


def load_config() -> AppConfig:
    """Load and merge all configuration sources."""
    return AppConfig(
        env=EnvSettings(),
        app_yaml=_load_yaml("app.yaml"),
        remote_yaml=_load_yaml("remote.yaml"),
        hadoop_yaml=_load_yaml("hadoop.yaml"),
        spark_yaml=_load_yaml("spark.yaml"),
        mongodb_yaml=_load_yaml("mongodb.yaml"),
        pipeline_yaml=_load_yaml("pipeline.yaml"),
    )
