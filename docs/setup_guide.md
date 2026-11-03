# Setup Guide

## Local Development (Windows)

### Prerequisites (already installed)
- Python 3.11+
- Git
- VS Code / Kiro IDE

### Steps

```bash
# Clone the repository (already on HDD)
cd "e:\BDA Project FMCG"

# Run unit tests (no external dependencies needed)
python -m pytest tests/unit/ -v

# Generate sample data
python scripts/generate_data.py --size small --output data/generated

# Validate the generated data
python scripts/validate_data.py --input data/generated
```

### What NOT to do locally
- Do NOT install Hadoop, Spark, or MongoDB on Windows
- Do NOT create large virtual environments on the SSD
- Do NOT run PySpark jobs locally
- Do NOT download large datasets to the SSD

## Remote Setup (Ubuntu 22.04)

See `docs/deployment_guide.md` for the complete remote installation guide.

### Quick start

```bash
# On the remote server:
bash scripts/remote/check_remote_environment.sh
bash scripts/remote/install_java.sh
bash scripts/remote/install_hadoop.sh
bash scripts/remote/install_spark.sh
bash scripts/remote/install_mongodb.sh
bash scripts/remote/configure_hadoop.sh
bash scripts/remote/configure_spark.sh
bash scripts/remote/configure_mongodb.sh
bash scripts/remote/start_services.sh
bash scripts/remote/verify_services.sh
bash scripts/remote/create_hdfs_dirs.sh
bash scripts/remote/deploy_application.sh
bash scripts/remote/run_pipeline.sh
```

### Access the Dashboard

```bash
# SSH tunnel from your local machine:
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 user@remote-server

# Open in browser:
# http://localhost:8501 (Streamlit)
# http://localhost:8000/docs (FastAPI docs)
```

## Configuration

All settings are in environment variables. Copy `.env.example` to `.env` and fill in values.

Key settings:
- `MONGO_HOST` — MongoDB host (default: localhost)
- `HDFS_NAMENODE_HOST` — HDFS NameNode (default: localhost)
- `SPARK_MASTER` — Spark master (default: yarn)
- `GENERATOR_SIZE` — dataset size preset (default: small)
