#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Stop All Services
# Stops YARN, HDFS, and MongoDB in reverse order.
# ============================================================

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"

echo "[stop_services] Stopping FMCG SupplyChainIQ services..."

# --- 1. YARN ---
echo ""
echo "[1/3] Stopping YARN..."
"$HADOOP_HOME/sbin/stop-yarn.sh" 2>/dev/null || true
echo "  YARN stopped."

# --- 2. HDFS ---
echo ""
echo "[2/3] Stopping HDFS..."
"$HADOOP_HOME/sbin/stop-dfs.sh" 2>/dev/null || true
echo "  HDFS stopped."

# --- 3. MongoDB ---
echo ""
echo "[3/3] Stopping MongoDB..."
sudo systemctl stop mongod 2>/dev/null || true
echo "  MongoDB stopped."

echo ""
echo "[stop_services] All services stopped."
