#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Install Apache Spark 4.0.5
# Downloads Spark pre-built for Hadoop 3 to /opt/spark.
# Configures SPARK_HOME and adds Spark binaries to PATH.
# Idempotent: skips if Spark 4.0.5 is already installed.
# ============================================================

set -euo pipefail

SPARK_VERSION="4.0.5"
SPARK_TARBALL="spark-${SPARK_VERSION}-bin-without-hadoop.tgz"
SPARK_URL="https://downloads.apache.org/spark/spark-${SPARK_VERSION}/${SPARK_TARBALL}"
SPARK_HOME="/opt/spark"
DOWNLOAD_DIR="/data/downloads"

echo "[install_spark] Installing Apache Spark ${SPARK_VERSION}..."

# Check if already installed
if [[ -d "$SPARK_HOME" && -f "$SPARK_HOME/bin/spark-submit" ]]; then
    INSTALLED_VERSION=$("$SPARK_HOME/bin/spark-submit" --version 2>&1 | grep "version" | head -1)
    if echo "$INSTALLED_VERSION" | grep -q "$SPARK_VERSION"; then
        echo "[install_spark] Spark ${SPARK_VERSION} already installed at ${SPARK_HOME}"
        exit 0
    fi
fi

# Download
if [[ ! -f "$DOWNLOAD_DIR/$SPARK_TARBALL" ]]; then
    echo "[install_spark] Downloading ${SPARK_TARBALL}..."
    wget -q -O "$DOWNLOAD_DIR/$SPARK_TARBALL" "$SPARK_URL"
fi

# Extract
echo "[install_spark] Extracting to ${SPARK_HOME}..."
sudo mkdir -p "$SPARK_HOME"
sudo tar -xzf "$DOWNLOAD_DIR/$SPARK_TARBALL" -C /opt/
if [[ -d "/opt/spark-${SPARK_VERSION}-bin-without-hadoop" ]]; then
    sudo rm -rf "$SPARK_HOME" 2>/dev/null || true
    sudo mv "/opt/spark-${SPARK_VERSION}-bin-without-hadoop" "$SPARK_HOME"
fi

# Set ownership
sudo chown -R "$(whoami):$(whoami)" "$SPARK_HOME"

# Add to PATH and set SPARK_HOME
if ! grep -q "SPARK_HOME" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'EOF'

# Spark
export SPARK_HOME=/opt/spark
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
export SPARK_CONF_DIR=$SPARK_HOME/conf
EOF
    echo "[install_spark] SPARK_HOME and PATH added to ~/.bashrc"
fi

export SPARK_HOME="$SPARK_HOME"
export PATH="$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin"

echo "[install_spark] Verification:"
"$SPARK_HOME/bin/spark-submit" --version 2>&1 | head -3
echo "[install_spark] Done. Run configure_spark.sh next."
