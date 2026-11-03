#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — CamberCloud Optional Profile
#
# CamberCloud is used ONLY for batch Spark/MLlib execution.
# It does NOT provide persistent HDFS, MongoDB, or public hosting.
# Stash is object storage, NOT a POSIX HDFS replacement.
#
# This script prepares data for CamberCloud execution:
#   1. Upload datasets to Stash
#   2. Submit Spark job to CamberCloud
#   3. Download results from Stash
#
# NEVER start a Camber job or spend credits without explicit approval.
# ============================================================

set -euo pipefail

echo "============================================"
echo "  FMCG SupplyChainIQ — CamberCloud Profile"
echo "============================================"
echo ""
echo "  This script prepares a CamberCloud batch execution."
echo "  CamberCloud is used ONLY for Spark batch jobs."
echo "  It does NOT replace HDFS or MongoDB."
echo ""
echo "  Stash is used as persistent object storage for"
echo "  datasets and result files between jobs."
echo ""
echo "  PREREQUISITES:"
echo "    - CamberCloud account with available credits"
echo "    - Datasets uploaded to Stash"
echo "    - PySpark job script ready"
echo ""
echo "  DO NOT run this script without explicit approval."
echo "  Do NOT spend Camber credits without permission."
echo ""

# --- Configuration ---
STASH_MOUNT="${STASH_MOUNT:-/stash/fmcg}"
SPARK_JOB="${1:-pipelines/spark/sales_analytics.py}"
SPARK_MASTER="local[*]"  # CamberCloud typically runs Spark in local mode

echo "  Stash mount: $STASH_MOUNT"
echo "  Spark job: $SPARK_JOB"
echo "  Spark master: $SPARK_MASTER"
echo ""

# --- Step 1: Verify data is in Stash ---
echo "[1/3] Checking Stash for input data..."
if [[ -d "$STASH_MOUNT/data" ]]; then
    echo "  Data found in Stash: $STASH_MOUNT/data"
    ls -la "$STASH_MOUNT/data/" | head -10
else
    echo "  No data found in Stash. Upload datasets first:"
    echo "    camber stash put data/generated/"
    exit 1
fi

# --- Step 2: Submit Spark job (REQUIRES APPROVAL) ---
echo ""
echo "[2/3] Spark job submission (REQUIRES EXPLICIT APPROVAL)"
echo "  To submit a Camber Spark job:"
echo "    camber spark create --script $SPARK_JOB --master $SPARK_MASTER"
echo ""
echo "  DO NOT submit without explicit approval."
echo "  DO NOT spend credits without permission."
echo ""

# --- Step 3: Download results ---
echo "[3/3] Download results from Stash"
echo "  After job completion, results are in Stash:"
echo "    camber stash get results/"
echo ""
echo "============================================"
echo "  CamberCloud profile complete."
echo "============================================"
