#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Verify All Services
# Checks that MongoDB, HDFS, YARN, and Spark are running.
# ============================================================

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
SPARK_HOME="${SPARK_HOME:-/opt/spark}"
PASS=0
FAIL=0

echo "============================================"
echo "  FMCG SupplyChainIQ — Service Verification"
echo "============================================"

# --- MongoDB ---
echo ""
echo "[MongoDB]"
if systemctl is-active --quiet mongod 2>/dev/null; then
    echo "  Status: RUNNING"
    if command -v mongosh &>/dev/null; then
        mongosh --quiet --eval "db.runCommand({ping:1})" 2>/dev/null | grep -q "ok" && echo "  Ping: OK" || echo "  Ping: FAILED"
    fi
    PASS=$((PASS+1))
else
    echo "  Status: NOT RUNNING"
    FAIL=$((FAIL+1))
fi

# --- HDFS NameNode ---
echo ""
echo "[HDFS NameNode]"
if jps 2>/dev/null | grep -q "NameNode"; then
    echo "  Status: RUNNING"
    PASS=$((PASS+1))
else
    echo "  Status: NOT RUNNING"
    FAIL=$((FAIL+1))
fi

# --- HDFS DataNode ---
echo ""
echo "[HDFS DataNode]"
if jps 2>/dev/null | grep -q "DataNode"; then
    echo "  Status: RUNNING"
    PASS=$((PASS+1))
else
    echo "  Status: NOT RUNNING"
    FAIL=$((FAIL+1))
fi

# --- YARN ResourceManager ---
echo ""
echo "[YARN ResourceManager]"
if jps 2>/dev/null | grep -q "ResourceManager"; then
    echo "  Status: RUNNING"
    PASS=$((PASS+1))
else
    echo "  Status: NOT RUNNING"
    FAIL=$((FAIL+1))
fi

# --- YARN NodeManager ---
echo ""
echo "[YARN NodeManager]"
if jps 2>/dev/null | grep -q "NodeManager"; then
    echo "  Status: RUNNING"
    PASS=$((PASS+1))
else
    echo "  Status: NOT RUNNING"
    FAIL=$((FAIL+1))
fi

# --- HDFS connectivity test ---
echo ""
echo "[HDFS Connectivity]"
if "$HADOOP_HOME/bin/hdfs" dfs -ls / &>/dev/null; then
    echo "  HDFS accessible: OK"
    PASS=$((PASS+1))
else
    echo "  HDFS not accessible"
    FAIL=$((FAIL+1))
fi

# --- Create HDFS directory structure ---
echo ""
echo "[HDFS Directory Structure]"
HDFS_ROOT="${HDFS_ROOT_PATH:-/fmcg-supplychainiq}"
"$HADOOP_HOME/bin/hdfs" dfs -mkdir -p "$HDFS_ROOT"/{raw,bronze,silver,gold,forecasts,metadata}
for layer in raw bronze silver gold forecasts metadata; do
    "$HADOOP_HOME/bin/hdfs" dfs -mkdir -p "$HDFS_ROOT/$layer" 2>/dev/null
done
echo "  HDFS directories created at $HDFS_ROOT"
PASS=$((PASS+1))

# --- Spark test ---
echo ""
echo "[Spark]"
if command -v spark-submit &>/dev/null || [[ -x "$SPARK_HOME/bin/spark-submit" ]]; then
    echo "  spark-submit: AVAILABLE"
    PASS=$((PASS+1))
else
    echo "  spark-submit: NOT FOUND"
    FAIL=$((FAIL+1))
fi

# --- Summary ---
echo ""
echo "============================================"
echo "  Results: $PASS passed, $FAIL failed"
if [[ "$FAIL" -eq 0 ]]; then
    echo "  ALL SERVICES RUNNING"
else
    echo "  SOME SERVICES NOT RUNNING — check above"
fi
echo "============================================"
