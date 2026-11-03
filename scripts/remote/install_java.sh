#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Install OpenJDK 17
# Java 17 LTS is required by both Hadoop 3.4.1 and Spark 4.0.x.
# Idempotent: skips if Java 17 is already installed.
# ============================================================

set -euo pipefail

JAVA_PACKAGE="openjdk-17-jdk-headless"
JAVA_HOME_PATH="/usr/lib/jvm/java-17-openjdk-amd64"

echo "[install_java] Installing OpenJDK 17..."

# Check if already installed
if java -version 2>&1 | grep -q '"17'; then
    echo "[install_java] Java 17 is already installed."
    java -version 2>&1 | head -1
    # Ensure JAVA_HOME is set
    if [[ -z "${JAVA_HOME:-}" ]]; then
        echo "export JAVA_HOME=$JAVA_HOME_PATH" >> ~/.bashrc
        echo "[install_java] Added JAVA_HOME to ~/.bashrc"
    fi
    exit 0
fi

# Update package list and install
sudo apt-get update -qq
sudo apt-get install -y "$JAVA_PACKAGE"

# Set JAVA_HOME
if ! grep -q "JAVA_HOME" ~/.bashrc 2>/dev/null; then
    echo "export JAVA_HOME=$JAVA_HOME_PATH" >> ~/.bashrc
    echo "[install_java] JAVA_HOME added to ~/.bashrc"
fi

export JAVA_HOME="$JAVA_HOME_PATH"

echo "[install_java] Verification:"
java -version 2>&1 | head -1
echo "JAVA_HOME=$JAVA_HOME"
echo "[install_java] Done."
