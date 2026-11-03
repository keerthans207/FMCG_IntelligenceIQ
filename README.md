# FMCG SupplyChainIQ

A Distributed FMCG Inventory Monitoring, Supply Chain Analytics and Demand Forecasting System Using MongoDB, Hadoop and Apache Spark.

## Overview

FMCG SupplyChainIQ is a Big Data intelligence platform that consolidates sales, inventory, batch, shipment, and stock movement data, processes it through MongoDB (operational), Hadoop HDFS (data lake), and Apache Spark (distributed processing), and provides analytics, anomaly detection, and demand forecasting.

## Architecture

```
Data Sources → Python Ingestion → MongoDB (operational) + HDFS (historical)
                                    ↓
                          Apache Spark (ETL, SQL, MLlib)
                                    ↓
                        Analytics & ML Outputs (HDFS gold)
                                    ↓
                        Result Publication → MongoDB
                                    ↓
                          FastAPI → Streamlit Dashboard
```

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| NoSQL Database | MongoDB Community | 8.0 |
| Distributed Storage | Hadoop HDFS + YARN | 3.4.1 |
| Distributed Processing | Apache Spark (PySpark) | 4.0.4 |
| ML Framework | Spark MLlib | 4.0.4 |
| Backend API | FastAPI | 0.115.x |
| Dashboard | Streamlit | 1.41.x |
| Language | Python | 3.11 |
| Java | OpenJDK | 17 (LTS) |
| OS (remote) | Ubuntu | 22.04 LTS |

## Project Structure

```
fmcg-supplychainiq/
├── configs/           YAML configuration files
├── data/
│   ├── sample/        Small sample datasets
│   ├── generated/     Generated datasets (gitignored)
│   └── schemas/       JSON schema definitions
├── docs/              Documentation
├── frontend/          Streamlit dashboard
├── pipelines/spark/   PySpark ETL and analytics jobs
├── scripts/
│   ├── generate_data.py     Synthetic data generator
│   ├── validate_data.py     Data validation
│   ├── pipeline/             Pipeline orchestrator
│   └── remote/              Remote deployment scripts
├── src/fmcg/          Core Python package
│   ├── config/        Configuration management
│   ├── database/      MongoDB connection & init
│   ├── ingestion/     MongoDB write utilities
│   ├── validation/    Schema validation
│   ├── analytics/     Inventory, expiry, shipment logic
│   ├── forecasting/   Feature engineering & evaluation
│   ├── anomaly/       Anomaly detection
│   ├── services/      Data access layer
│   ├── api/           FastAPI application
│   └── models/        Pydantic schemas
├── tests/             Unit, integration, end-to-end tests
├── deployment/         Deployment configurations
└── artifacts/         Reports and metrics (gitignored)
```

## Local Development (Windows)

The Windows laptop is used **only** for:
- Editing source code with Kiro IDE
- Git operations
- Running lightweight unit tests (no Spark/MongoDB required)
- SSH connectivity to the remote server

```bash
# Install lightweight dev dependencies (already installed packages suffice)
# Run unit tests (no Spark or MongoDB needed):
python -m pytest tests/unit/ -v

# Generate sample data (lightweight):
python scripts/generate_data.py --size small --output data/generated

# Validate generated data:
python scripts/validate_data.py --input data/generated
```

## Remote Deployment (Ubuntu Linux)

All Big Data infrastructure runs on a remote Ubuntu server.

### Prerequisites
- Ubuntu 22.04 LTS (EC2 or college server)
- Minimum 4 GB RAM, 2 vCPUs, 50 GB disk
- SSH access

### Installation

```bash
# On the remote server:
cd /opt/fmcg-supplychainiq

# Install the full stack:
bash scripts/remote/check_remote_environment.sh
bash scripts/remote/install_java.sh
bash scripts/remote/install_hadoop.sh
bash scripts/remote/install_spark.sh
bash scripts/remote/install_mongodb.sh

# Configure:
bash scripts/remote/configure_hadoop.sh
bash scripts/remote/configure_spark.sh

# Start services:
bash scripts/remote/start_services.sh
bash scripts/remote/verify_services.sh

# Deploy application:
bash scripts/remote/deploy_application.sh

# Run the pipeline:
bash scripts/remote/run_pipeline.sh
```

### Running the Pipeline

```bash
# Full pipeline:
python scripts/pipeline/run_pipeline.py

# Specific stages:
python scripts/pipeline/run_pipeline.py --stages generate_data ingest_mongo

# Start FastAPI:
uvicorn fmcg.api.main:app --host 0.0.0.0 --port 8000

# Start Streamlit (via SSH tunnel):
streamlit run frontend/app.py --server.port 8501
```

## Testing

```bash
# Unit tests (local, no dependencies needed):
python -m pytest tests/unit/ -v

# Integration tests (require remote services):
python -m pytest tests/integration/ -v -m integration

# End-to-end tests (require full remote stack):
python -m pytest tests/end_to_end/ -v
```

## Configuration

All configuration is driven by environment variables (`.env` file) and YAML files in `configs/`. See `.env.example` for all available settings.

## License

MIT (academic project)
