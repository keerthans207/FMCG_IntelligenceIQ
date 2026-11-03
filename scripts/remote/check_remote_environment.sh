#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Remote Environment Checker
# Verifies the remote server meets all prerequisites.
# Safe to run multiple times. Does not install anything.
# ============================================================

set -euo pipefail

echo "============================================"
echo "  FMCG SupplyChainIQ — Environment Check"
echo "============================================"

# --- OS ---
echo ""
echo "[OS]"
. /etc/os-release
echo "  Distribution: $NAME"
echo "  Version: $VERSION"
if [[ "$VERSION_ID" != "22.04" ]]; then
    echo "  WARNING: Recommended Ubuntu 22.04 LTS, found $VERSION_ID"
fi

# --- CPU ---
echo ""
echo "[CPU]"
CPU_COUNT=$(nproc)
echo "  vCPUs: $CPU_COUNT"
if [[ "$CPU_COUNT" -lt 2 ]]; then
    echo "  WARNING: Minimum 2 vCPUs recommended"
fi

# --- RAM ---
echo ""
echo "[Memory]"
TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
echo "  Total RAM: ${TOTAL_MEM} GB"
if [[ "$TOTAL_MEM" -lt 3 ]]; then
    echo "  WARNING: Minimum 4 GB RAM recommended for Hadoop + Spark + MongoDB"
fi

# --- Disk ---
echo ""
echo "[Disk]"
ROOT_AVAIL=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
echo "  Root partition available: ${ROOT_AVAIL} GB"
DATA_DIR="/data"
if [[ -d "$DATA_DIR" ]]; then
    DATA_AVAIL=$(df -BG "$DATA_DIR" | awk 'NR==2{print $4}' | tr -d 'G')
    echo "  /data available: ${DATA_AVAIL} GB"
else
    echo "  /data does not exist yet (will be created during install)"
fi
if [[ "$ROOT_AVAIL" -lt 20 ]]; then
    echo "  WARNING: Minimum 20 GB free disk space recommended"
fi

# --- Java ---
echo ""
echo "[Java]"
if command -v java &>/dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    echo "  Installed: $JAVA_VERSION"
else
    echo "  NOT installed (will be installed by install_java.sh)"
fi

# --- Python ---
echo ""
echo "[Python]"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    echo "  $PY_VERSION"
else
    echo "  NOT installed"
fi

# --- Hadoop ---
echo ""
echo "[Hadoop]"
if command -v hdfs &>/dev/null; then
    HADOOP_VERSION=$(hdfs version 2>&1 | head -1)
    echo "  Installed: $HADOOP_VERSION"
else
    echo "  NOT installed (will be installed by install_hadoop.sh)"
fi

# --- Spark ---
echo ""
echo "[Spark]"
if command -v spark-submit &>/dev/null; then
    SPARK_VERSION=$(spark-submit --version 2>&1 | grep "version" | head -1)
    echo "  Installed: $SPARK_VERSION"
else
    echo "  NOT installed (will be installed by install_spark.sh)"
fi

# --- MongoDB ---
echo ""
echo "[MongoDB]"
if command -v mongod &>/dev/null; then
    MONGO_VERSION=$(mongod --version 2>&1 | head -1)
    echo "  Installed: $MONGO_VERSION"
else
    echo "  NOT installed (will be installed by install_mongodb.sh)"
fi

# --- Network ---
echo ""
echo "[Network]"
echo "  Hostname: $(hostname)"
echo "  IP addresses:"
hostname -I 2>/dev/null | tr ' ' '\n' | while read -r ip; do
    [[ -n "$ip" ]] && echo "    - $ip"
done

# --- Firewall ---
echo ""
echo "[Firewall]"
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null || echo "inactive")
    echo "  UFW: $UFW_STATUS"
else
    echo "  UFW not available"
fi

echo ""
echo "============================================"
echo "  Environment check complete."
echo "  Review any WARNINGs above before proceeding."
echo "============================================"
