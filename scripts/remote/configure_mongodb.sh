#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Configure MongoDB
# Sets up mongod.conf with bind IP, data directory, and
# authentication settings for academic single-node deployment.
# MongoDB is NOT exposed publicly — bound to localhost only.
# ============================================================

set -euo pipefail

MONGO_DATA_DIR="${MONGODB_DATA_DIR:-/data/mongodb}"
MONGO_CONF="/etc/mongod.conf"

echo "[configure_mongodb] Configuring MongoDB..."

# Create data directory
sudo mkdir -p "$MONGO_DATA_DIR"
sudo chown -R mongodb:mongodb "$MONGO_DATA_DIR"

# Write mongod.conf
sudo tee "$MONGO_CONF" > /dev/null << EOF
# MongoDB configuration for FMCG SupplyChainIQ
storage:
  dbPath: ${MONGO_DATA_DIR}
  journal:
    enabled: true

systemLog:
  destination: file
  path: /data/fmcg/logs/mongodb/mongod.log
  logAppend: true

net:
  port: 27017
  bindIp: 127.0.0.1
  # MongoDB is NOT publicly exposed.
  # Access via SSH tunnel or local application only.

processManagement:
  fork: true
  pidFilePath: /var/run/mongodb/mongod.pid

security:
  authorization: disabled
  # Enable authorization for production deployments.
  # For academic demo, disabled for simplicity.
EOF

# Create log directory
sudo mkdir -p /data/fmcg/logs/mongodb
sudo chown -R mongodb:mongodb /data/fmcg/logs/mongodb

echo "[configure_mongodb] MongoDB configured:"
echo "  Data directory: $MONGO_DATA_DIR"
echo "  Config file: $MONGO_CONF"
echo "  Bind IP: 127.0.0.1 (localhost only — NOT publicly exposed)"
echo "  Port: 27017"
echo "[configure_mongodb] Done."
