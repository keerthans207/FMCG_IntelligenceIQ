#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Run Pipeline
# Executes the full data pipeline on the remote server.
# ============================================================

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/fmcg-supplychainiq}"
VENV_DIR="${PYTHON_VENV:-/opt/fmcg-venv}"

echo "[run_pipeline] Running FMCG SupplyChainIQ pipeline..."

# Activate virtual environment
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"

# Load environment variables
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
fi

# Run the pipeline orchestrator
python scripts/pipeline/run_pipeline.py "$@"

echo "[run_pipeline] Pipeline execution finished."
