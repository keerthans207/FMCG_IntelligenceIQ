#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Deploy Application
# Sets up the Python virtual environment, installs dependencies,
# and prepares the application for running.
# ============================================================

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/fmcg-supplychainiq}"
VENV_DIR="${PYTHON_VENV:-/opt/fmcg-venv}"

echo "[deploy_application] Deploying FMCG SupplyChainIQ application..."

# Create virtual environment
echo ""
echo "[1/4] Creating Python virtual environment at $VENV_DIR..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "  Virtual environment created."
else
    echo "  Virtual environment already exists."
fi

# Activate and install
echo ""
echo "[2/4] Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$PROJECT_DIR/requirements.txt" --quiet
echo "  Dependencies installed."

# Initialize MongoDB database
echo ""
echo "[3/4] Initializing MongoDB database..."
python -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/src')
from fmcg.database.init_db import init_database
result = init_database()
print('  Collections:', list(result['collections'].keys()))
print('  Database initialized.')
"
echo "  MongoDB initialized."

# Create application directories
echo ""
echo "[4/4] Creating application directories..."
mkdir -p /data/fmcg/{models,logs,checkpoints}
mkdir -p /data/fmcg/logs/{spark,mongodb,api}
echo "  Directories created."

echo ""
echo "[deploy_application] Deployment complete."
echo "  Virtual env: $VENV_DIR"
echo "  Project dir: $PROJECT_DIR"
echo ""
echo "  Next steps:"
echo "    1. Start services: bash scripts/remote/start_services.sh"
echo "    2. Run pipeline:   bash scripts/remote/run_pipeline.sh"
echo "    3. Start API:      source $VENV_DIR/bin/activate && uvicorn fmcg.api.main:app --port 8000"
echo "    4. Start dashboard: source $VENV_DIR/bin/activate && streamlit run frontend/app.py --server.port 8501"
