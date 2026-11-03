#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Start All Services
# Starts MongoDB, Hadoop HDFS, Hadoop YARN in order.
# ============================================================

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"

echo "[start_services] Starting FMCG SupplyChainIQ services..."

# --- 1. MongoDB ---
echo ""
echo "[1/3] Starting MongoDB..."
if systemctl is-active --quiet mongod 2>/dev/null; then
    echo "  MongoDB is already running."
else
    sudo systemctl start mongod
    sleep 2
    if systemctl is-active --quiet mongod; then
        echo "  MongoDB started."
    else
        echo "  FAILED: MongoDB did not start."
        exit 1
    fi
fi

# --- 2. Hadoop HDFS ---
echo ""
echo "[2/3] Starting Hadoop HDFS..."
# Format NameNode if not already formatted
if [[ ! -d "${HADOOP_NAMENODE_DIR:-/data/hadoop/namenode}/current" ]]; then
    echo "  Formatting NameNode (first run)..."
    "$HADOOP_HOME/bin/hdfs" namenode -format -force -nonInteractive
fi

"$HADOOP_HOME/sbin/start-dfs.sh"
sleep 2
echo "  HDFS started."

# --- 3. Hadoop YARN ---
echo ""
echo "[3/3] Starting Hadoop YARN..."
"$HADOOP_HOME/sbin/start-yarn.sh"
sleep 2
echo "  YARN started."

echo ""
echo "[start_services] All services started."
echo "  Run verify_services.sh to confirm."
