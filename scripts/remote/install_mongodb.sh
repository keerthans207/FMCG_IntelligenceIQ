#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Install MongoDB 8.0 Community Edition
# Adds the official MongoDB apt repository and installs
# the mongodb-org metapackage.
# Idempotent: skips if MongoDB 8.0 is already installed.
# ============================================================

set -euo pipefail

MONGO_VERSION="8.0"

echo "[install_mongodb] Installing MongoDB ${MONGO_VERSION} Community Edition..."

# Check if already installed
if command -v mongod &>/dev/null; then
    INSTALLED_VERSION=$(mongod --version 2>&1 | head -1)
    if echo "$INSTALLED_VERSION" | grep -q "db version v${MONGO_VERSION}"; then
        echo "[install_mongodb] MongoDB ${MONGO_VERSION} already installed."
        echo "$INSTALLED_VERSION"
        exit 0
    fi
fi

# Install prerequisites
sudo apt-get update -qq
sudo apt-get install -y gnupg curl

# Add MongoDB GPG key
echo "[install_mongodb] Adding MongoDB GPG key..."
curl -fsSL https://www.mongodb.org/static/pgp/server-${MONGO_VERSION}.asc | \
    sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/mongodb-server-${MONGO_VERSION}.gpg

# Add MongoDB repository
echo "[install_mongodb] Adding MongoDB repository..."
UBUNTU_CODENAME=$(. /etc/os-release && echo "$UBUNTU_CODENAME")
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-${MONGO_VERSION}.gpg ] https://repo.mongodb.org/apt/ubuntu ${UBUNTU_CODENAME}/mongodb-org/${MONGO_VERSION} multiverse" | \
    sudo tee /etc/apt/sources.list.d/mongodb-org-${MONGO_VERSION}.list

# Install MongoDB
sudo apt-get update -qq
sudo apt-get install -y mongodb-org

# Create data directory
sudo mkdir -p /data/mongodb
sudo chown -R mongodb:mongodb /data/mongodb

echo "[install_mongodb] Verification:"
mongod --version 2>&1 | head -1
echo "[install_mongodb] Done. Run configure_mongodb.sh next."
