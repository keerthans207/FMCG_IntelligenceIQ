#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Install Apache Hadoop 3.5.0
# Downloads and extracts Hadoop to /opt/hadoop.
# Configures HADOOP_HOME and adds Hadoop binaries to PATH.
# Idempotent: skips if Hadoop 3.5.0 is already installed.
# ============================================================

set -euo pipefail

HADOOP_VERSION="3.5.0"
HADOOP_TARBALL="hadoop-${HADOOP_VERSION}.tar.gz"
HADOOP_URL="https://downloads.apache.org/hadoop/common/stable/${HADOOP_TARBALL}"
HADOOP_HOME="/opt/hadoop"
DOWNLOAD_DIR="/data/downloads"

echo "[install_hadoop] Installing Apache Hadoop ${HADOOP_VERSION}..."

# Check if already installed
if [[ -d "$HADOOP_HOME" && -f "$HADOOP_HOME/bin/hdfs" ]]; then
    INSTALLED_VERSION=$("$HADOOP_HOME/bin/hdfs" version 2>&1 | head -1)
    if echo "$INSTALLED_VERSION" | grep -q "$HADOOP_VERSION"; then
        echo "[install_hadoop] Hadoop ${HADOOP_VERSION} already installed at ${HADOOP_HOME}"
        exit 0
    fi
fi

# Download
if [[ ! -f "$DOWNLOAD_DIR/$HADOOP_TARBALL" ]]; then
    echo "[install_hadoop] Downloading ${HADOOP_TARBALL}..."
    wget -q -O "$DOWNLOAD_DIR/$HADOOP_TARBALL" "$HADOOP_URL"
fi

# Extract
echo "[install_hadoop] Extracting to ${HADOOP_HOME}..."
sudo mkdir -p "$HADOOP_HOME"
sudo tar -xzf "$DOWNLOAD_DIR/$HADOOP_TARBALL" -C /opt/
# The tarball extracts to hadoop-3.5.0; move to hadoop
if [[ -d "/opt/hadoop-${HADOOP_VERSION}" ]]; then
    sudo rm -rf "$HADOOP_HOME" 2>/dev/null || true
    sudo mv "/opt/hadoop-${HADOOP_VERSION}" "$HADOOP_HOME"
fi

# Set ownership to current user
sudo chown -R "$(whoami):$(whoami)" "$HADOOP_HOME"

# Add to PATH and set HADOOP_HOME
if ! grep -q "HADOOP_HOME" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'EOF'

# Hadoop
export HADOOP_HOME=/opt/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"
EOF
    echo "[install_hadoop] HADOOP_HOME and PATH added to ~/.bashrc"
fi

export HADOOP_HOME="$HADOOP_HOME"
export PATH="$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin"

echo "[install_hadoop] Verification:"
"$HADOOP_HOME/bin/hadoop" version 2>&1 | head -1
echo "[install_hadoop] Done. Run configure_hadoop.sh next."
