#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Configure Apache Spark
# Writes spark-env.sh and spark-defaults.conf for YARN mode.
# ============================================================

set -euo pipefail

SPARK_HOME="${SPARK_HOME:-/opt/spark}"
SPARK_CONF="$SPARK_HOME/conf"
HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"

echo "[configure_spark] Configuring Spark..."

# --- spark-env.sh ---
cat > "$SPARK_CONF/spark-env.sh" << EOF
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}
export HADOOP_HOME=${HADOOP_HOME}
export HADOOP_CONF_DIR=${HADOOP_CONF_DIR}
export SPARK_MASTER_HOST=localhost
export SPARK_LOCAL_DIRS=/data/spark/tmp
export SPARK_WORKER_DIR=/data/spark/work
export SPARK_LOG_DIR=/data/fmcg/logs/spark
export PYSPARK_PYTHON=python3
export PYSPARK_DRIVER_PYTHON=python3
EOF

chmod +x "$SPARK_CONF/spark-env.sh"

# --- spark-defaults.conf ---
cat > "$SPARK_CONF/spark-defaults.conf" << EOF
# Spark defaults for FMCG SupplyChainIQ
spark.master                     yarn
spark.deploy.mode                client
spark.driver.memory              2g
spark.executor.memory            2g
spark.executor.cores             2
spark.executor.instances         2
spark.yarn.queue                  default
spark.sql.shuffle.partitions     32
spark.sql.adaptive.enabled       true
spark.sql.parquet.compression.codec snappy
spark.eventLog.enabled           false
EOF

# Create Spark temp directories
sudo mkdir -p /data/spark/tmp /data/spark/work /data/fmcg/logs/spark
sudo chown -R "$(whoami):$(whoami)" /data/spark /data/fmcg/logs

echo "[configure_spark] Configuration written to $SPARK_CONF"
echo "[configure_spark] Master: yarn (client mode)"
echo "[configure_spark] Done."
