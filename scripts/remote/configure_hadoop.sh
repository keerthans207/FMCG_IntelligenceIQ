#!/bin/bash
# ============================================================
# FMCG SupplyChainIQ — Configure Hadoop HDFS + YARN
# Writes core-site.xml, hdfs-site.xml, yarn-site.xml for
# single-node academic deployment.
# Replication = 1 (single node — no fault tolerance).
# ============================================================

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HADOOP_CONF="$HADOOP_HOME/etc/hadoop"
NAMENODE_HOST="${HDFS_NAMENODE_HOST:-localhost}"
NAMENODE_PORT="${HDFS_NAMENODE_PORT:-9000}"
HDFS_ROOT="${HDFS_ROOT_PATH:-/fmcg-supplychainiq}"
NAMENODE_DIR="${HADOOP_NAMENODE_DIR:-/data/hadoop/namenode}"
DATANODE_DIR="${HADOOP_DATANODE_DIR:-/data/hadoop/datanode}"

echo "[configure_hadoop] Configuring Hadoop..."

# Create data directories
sudo mkdir -p "$NAMENODE_DIR" "$DATANODE_DIR"
sudo chown -R "$(whoami):$(whoami)" /data/hadoop

# --- core-site.xml ---
cat > "$HADOOP_CONF/core-site.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://${NAMENODE_HOST}:${NAMENODE_PORT}</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/data/hadoop/tmp</value>
    </property>
</configuration>
EOF

# --- hdfs-site.xml ---
cat > "$HADOOP_CONF/hdfs-site.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
        <!-- Single-node academic deployment: replication=1. No fault tolerance. -->
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://${NAMENODE_DIR}</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://${DATANODE_DIR}</value>
    </property>
    <property>
        <name>dfs.blocksize</name>
        <value>128m</value>
    </property>
    <property>
        <name>dfs.namenode.http-address</name>
        <value>0.0.0.0:9870</value>
    </property>
</configuration>
EOF

# --- yarn-site.xml ---
cat > "$HADOOP_CONF/yarn-site.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>localhost</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.scheduler.minimum-allocation-mb</name>
        <value>512</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-mb</name>
        <value>4096</value>
    </property>
    <property>
        <name>yarn.nodemanager.resource.memory-mb</name>
        <value>4096</value>
    </property>
    <property>
        <name>yarn.nodemanager.vmem-check-enabled</name>
        <value>false</value>
    </property>
    <property>
        <name>yarn.log-aggregation-enable</name>
        <value>true</value>
    </property>
</configuration>
EOF

# --- mapred-site.xml ---
cat > "$HADOOP_CONF/mapred-site.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
    <property>
        <name>mapreduce.application.classpath</name>
        <value>\$HADOOP_HOME/share/hadoop/mapreduce/*:\$HADOOP_HOME/share/hadoop/mapreduce/lib/*</value>
    </property>
</configuration>
EOF

# --- hadoop-env.sh ---
JAVA_HOME_PATH="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
cat > "$HADOOP_CONF/hadoop-env.sh" << EOF
export JAVA_HOME=${JAVA_HOME_PATH}
export HADOOP_HOME=${HADOOP_HOME}
export HADOOP_CONF_DIR=${HADOOP_CONF}
export HADOOP_COMMON_LIB_NATIVE_DIR=\${HADOOP_HOME}/lib/native
export HADOOP_OPTS="-Djava.library.path=\${HADOOP_HOME}/lib/native"
EOF

echo "[configure_hadoop] Configuration written to $HADOOP_CONF"
echo "[configure_hadoop] Replication: 1 (single-node academic deployment)"
echo "[configure_hadoop] NameNode dir: $NAMENODE_DIR"
echo "[configure_hadoop] DataNode dir: $DATANODE_DIR"
echo "[configure_hadoop] Done. Format the NameNode before first start:"
echo "  $HADOOP_HOME/bin/hdfs namenode -format"
