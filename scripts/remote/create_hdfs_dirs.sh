#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Create HDFS Directory Structure
# Creates the medallion architecture directory layout in HDFS.
# Idempotent: safe to run multiple times.
# ============================================================

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HDFS_ROOT="${HDFS_ROOT_PATH:-/fmcg-supplychainiq}"
HDFS="$HADOOP_HOME/bin/hdfs"

echo "[create_hdfs_dirs] Creating HDFS directory structure at $HDFS_ROOT..."

# Root
$HDFS dfs -mkdir -p "$HDFS_ROOT"

# Raw layer
$HDFS dfs -mkdir -p "$HDFS_ROOT/raw"/{products,locations,suppliers,batches,sales,inventory,shipments,stock_movements}

# Bronze layer
$HDFS dfs -mkdir -p "$HDFS_ROOT/bronze"/{sales,inventory,batches,shipments}

# Silver layer
$HDFS dfs -mkdir -p "$HDFS_ROOT/silver"/{cleaned_sales,validated_inventory,standardized_batches,validated_shipments}

# Gold layer
$HDFS dfs -mkdir -p "$HDFS_ROOT/gold"/{inventory_analytics,demand_analytics,expiry_analytics,shipment_analytics,anomaly_analytics}

# Forecasts
$HDFS dfs -mkdir -p "$HDFS_ROOT/forecasts"/{training,predictions,evaluation}

# Metadata
$HDFS dfs -mkdir -p "$HDFS_ROOT/metadata"/{schemas,manifests,pipeline_runs}

echo ""
echo "[create_hdfs_dirs] HDFS directory structure created:"
$HDFS dfs -ls -R "$HDFS_ROOT" | head -40

echo ""
echo "[create_hdfs_dirs] Done."
