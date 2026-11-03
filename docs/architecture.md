# System Architecture

## Overview

FMCG SupplyChainIQ uses a layered architecture that separates operational data (MongoDB), historical storage (HDFS), distributed processing (Spark), and application interfaces (FastAPI/Streamlit).

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│  Products · Sales · Inventory · Batches · Shipments      │
│  Stock Movements · Suppliers · Locations                  │
└──────────────────────┬──────────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │  PYTHON DATA INGESTION │
           │  (scripts/pipeline/)   │
           └─────┬─────────┬───────┘
                 │           │
     ┌───────────▼──┐   ┌───▼──────────────┐
     │   MONGODB     │   │  HADOOP HDFS    │
     │  Operational  │   │  Historical     │
     │  Database     │   │  Data Lake      │
     └───────┬───────┘   └───────┬────────┘
             │                   │
             │          ┌────────▼────────┐
             │          │  APACHE SPARK    │
             │          │  ETL · SQL · ML  │
             │          │  DataFrames      │
             │          │  MLlib           │
             │          └────────┬────────┘
             │                   │
             │     ┌─────────────▼──────────────┐
             │     │  ANALYTICS & ML OUTPUTS     │
             │     │  (HDFS Gold + Forecasts)    │
             │     └─────────────┬──────────────┘
             │                   │
     ┌───────▼───────────────────▼──┐
     │     RESULT PUBLICATION        │
     │  (Python → MongoDB)           │
     └───────────────┬──────────────┘
                     │
             ┌───────▼───────┐
             │   FASTAPI      │
             │   REST API     │
             └───────┬───────┘
                     │
             ┌───────▼───────┐
             │  STREAMLIT     │
             │  DASHBOARD     │
             └───────────────┘
```

## Why MongoDB, Hadoop, and Spark?

### MongoDB (NoSQL Operational Database)

MongoDB stores operational records that require low-latency reads/writes: product catalogs, current inventory, sales transactions, shipment records, and analytics results for the dashboard.

- **Schema flexibility**: FMCG data has varying structures per entity type.
- **Fast queries**: Indexed queries for real-time dashboard reads.
- **JSON-native**: Natural fit for API responses.

### Hadoop HDFS (Distributed Data Lake)

HDFS stores historical and large-scale datasets for batch processing. Raw data, bronze/silver/gold medallion layers, and ML training data all live in HDFS.

- **Distributed storage**: Scales horizontally as data grows.
- **Write-once, read-many**: Efficient for batch analytics.
- **Parquet format**: Columnar storage for fast Spark reads.

### Apache Spark (Distributed Processing)

Spark processes data at scale using DataFrames, Spark SQL, and MLlib. It reads from HDFS, transforms data through the medallion layers, and writes analytical outputs back.

- **In-memory processing**: Faster than disk-based MapReduce.
- **Unified API**: ETL, SQL, and ML in one framework.
- **MLlib**: Native distributed ML for demand forecasting.

## NoSQL vs HDFS vs Spark

| Aspect | MongoDB | HDFS | Spark |
|---|---|---|---|
| Role | Operational DB | Data lake | Processing engine |
| Data model | Document (BSON) | File (Parquet/JSONL) | DataFrame |
| Access pattern | Random read/write | Sequential read | Batch transformation |
| Latency | Milliseconds | Seconds-minutes | Minutes-hours |
| Scale | Vertical + sharding | Horizontal (DataNodes) | Horizontal (executors) |

## Medallion Architecture (HDFS Layers)

```
raw/        → Verbatim source records (JSONL)
bronze/     → Raw loaded, minimal type coercion
silver/     → Cleaned, validated, deduplicated (Parquet)
gold/       → Aggregated analytics ready for consumption (Parquet)
forecasts/  → ML training data, predictions, evaluation
metadata/   → Schemas, manifests, pipeline run logs
```

## Single-Node Academic Deployment

The initial deployment is a single-node Hadoop cluster (replication=1). This does NOT provide fault tolerance or high availability. It is suitable for academic demonstration and performance benchmarking on one machine.

## Data Flow: MongoDB ↔ HDFS

1. Python ingestion writes operational records to MongoDB.
2. Batch export extracts records from MongoDB to JSONL.
3. JSONL files are uploaded to HDFS raw layer.
4. Spark reads from HDFS, processes through medallion layers.
5. Spark writes analytical outputs to HDFS gold layer.
6. Python publication process writes selected results back to MongoDB.
7. FastAPI reads from MongoDB for dashboard queries.

This approach uses PyMongo for export/import — no MongoDB Spark Connector required.
