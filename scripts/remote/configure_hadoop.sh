#!/usr/bin/env bash

set -euo pipefail

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HADOOP_CONF="$HADOOP_HOME/etc/hadoop"
JAVA_HOME_PATH="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"

NAMENODE_HOST="${HDFS_NAMENODE_HOST:-localhost}"
NAMENODE_PORT="${HDFS_NAMENODE_PORT:-9000}"

NAMENODE_DIR="/data/hadoop/namenode"
DATANODE_DIR="/data/hadoop/datanode"
HADOOP_TMP="/data/hadoop/tmp"

YARN_LOCAL="/data/yarn/local"
YARN_LOGS="/data/yarn/logs"

echo "[configure_hadoop] Starting configuration..."

if [[ ! -x "$HADOOP_HOME/bin/hdfs" ]]; then
    echo "ERROR: Hadoop not found at $HADOOP_HOME"
    exit 1
fi

if ! java -version 2>&1 | grep -q '"17'; then
    echo "ERROR: Java 17 is required."
    exit 1
fi

# Create persistent data directories.
sudo mkdir -p \
    "$NAMENODE_DIR" \
    "$DATANODE_DIR" \
    "$HADOOP_TMP" \
    "$YARN_LOCAL" \
    "$YARN_LOGS"

sudo chown -R "$(id -un):$(id -gn)" /data/hadoop /data/yarn

# CORE SITE
cat > "$HADOOP_CONF/core-site.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://${NAMENODE_HOST}:${NAMENODE_PORT}</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>${HADOOP_TMP}</value>
    </property>
    <property>
        <name>io.file.buffer.size</name>
        <value>131072</value>
    </property>
</configuration>
XML

# HDFS
cat > "$HADOOP_CONF/hdfs-site.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
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
        <value>67108864</value>
    </property>
    <property>
        <name>dfs.namenode.rpc-address</name>
        <value>${NAMENODE_HOST}:${NAMENODE_PORT}</value>
    </property>
    <property>
        <name>dfs.namenode.http-address</name>
        <value>127.0.0.1:9870</value>
    </property>
    <property>
        <name>dfs.datanode.address</name>
        <value>127.0.0.1:9866</value>
    </property>
    <property>
        <name>dfs.datanode.http.address</name>
        <value>127.0.0.1:9864</value>
    </property>
</configuration>
XML

# YARN - conservative memory for 8 GiB EC2.
cat > "$HADOOP_CONF/yarn-site.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>localhost</value>
    </property>
    <property>
        <name>yarn.resourcemanager.webapp.address</name>
        <value>127.0.0.1:8088</value>
    </property>
    <property>
        <name>yarn.nodemanager.webapp.address</name>
        <value>127.0.0.1:8042</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.nodemanager.env-whitelist</name>
        <value>JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_HOME,HADOOP_MAPRED_HOME,PATH,LANG,TZ</value>
    </property>
    <property>
        <name>yarn.nodemanager.resource.memory-mb</name>
        <value>3072</value>
    </property>
    <property>
        <name>yarn.scheduler.minimum-allocation-mb</name>
        <value>512</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-mb</name>
        <value>3072</value>
    </property>
    <property>
        <name>yarn.nodemanager.resource.cpu-vcores</name>
        <value>2</value>
    </property>
    <property>
        <name>yarn.scheduler.minimum-allocation-vcores</name>
        <value>1</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-vcores</name>
        <value>2</value>
    </property>
    <property>
        <name>yarn.nodemanager.local-dirs</name>
        <value>${YARN_LOCAL}</value>
    </property>
    <property>
        <name>yarn.nodemanager.log-dirs</name>
        <value>${YARN_LOGS}</value>
    </property>
    <property>
        <name>yarn.nodemanager.pmem-check-enabled</name>
        <value>true</value>
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
XML

# MapReduce on YARN
cat > "$HADOOP_CONF/mapred-site.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
    <property>
        <name>mapreduce.application.classpath</name>
        <value>${HADOOP_HOME}/share/hadoop/mapreduce/*:${HADOOP_HOME}/share/hadoop/mapreduce/lib/*</value>
    </property>
    <property>
        <name>yarn.app.mapreduce.am.resource.memory-mb</name>
        <value>512</value>
    </property>
    <property>
        <name>yarn.app.mapreduce.am.command-opts</name>
        <value>-Xmx384m</value>
    </property>
    <property>
        <name>mapreduce.map.memory.mb</name>
        <value>512</value>
    </property>
    <property>
        <name>mapreduce.map.java.opts</name>
        <value>-Xmx384m</value>
    </property>
    <property>
        <name>mapreduce.reduce.memory.mb</name>
        <value>512</value>
    </property>
    <property>
        <name>mapreduce.reduce.java.opts</name>
        <value>-Xmx384m</value>
    </property>
</configuration>
XML

# Preserve the default hadoop-env.sh and append our settings once.
if ! grep -q 'FMCG SUPPLYCHAINIQ ENVIRONMENT' "$HADOOP_CONF/hadoop-env.sh"; then
cat >> "$HADOOP_CONF/hadoop-env.sh" <<ENV

# FMCG SUPPLYCHAINIQ ENVIRONMENT
export JAVA_HOME="${JAVA_HOME_PATH}"
export HADOOP_HOME="${HADOOP_HOME}"
export HADOOP_CONF_DIR="${HADOOP_CONF}"
export HADOOP_MAPRED_HOME="${HADOOP_HOME}"
export HADOOP_HEAPSIZE_MAX=512
export HADOOP_NAMENODE_OPTS="\${HADOOP_NAMENODE_OPTS:-} -Xms256m -Xmx512m"
export HADOOP_DATANODE_OPTS="\${HADOOP_DATANODE_OPTS:-} -Xms256m -Xmx512m"
export HADOOP_SECONDARYNAMENODE_OPTS="\${HADOOP_SECONDARYNAMENODE_OPTS:-} -Xms128m -Xmx256m"
ENV
fi

# Set YARN daemon heap sizes once.
if ! grep -q 'FMCG SUPPLYCHAINIQ YARN MEMORY' "$HADOOP_CONF/yarn-env.sh"; then
cat >> "$HADOOP_CONF/yarn-env.sh" <<'ENV'

# FMCG SUPPLYCHAINIQ YARN MEMORY
export YARN_RESOURCEMANAGER_HEAPSIZE=512
export YARN_NODEMANAGER_HEAPSIZE=512
ENV
fi

# One local worker.
printf 'localhost\n' > "$HADOOP_CONF/workers"

# Persistent shell environment.
if ! grep -q 'FMCG SUPPLYCHAINIQ PATH' "$HOME/.bashrc"; then
cat >> "$HOME/.bashrc" <<ENV

# FMCG SUPPLYCHAINIQ PATH
export JAVA_HOME="${JAVA_HOME_PATH}"
export HADOOP_HOME="${HADOOP_HOME}"
export HADOOP_CONF_DIR="\$HADOOP_HOME/etc/hadoop"
export HADOOP_MAPRED_HOME="\$HADOOP_HOME"
export PATH="\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin"
ENV
fi

echo "[configure_hadoop] Configuration completed."
echo "HDFS NameNode: ${NAMENODE_DIR}"
echo "HDFS DataNode: ${DATANODE_DIR}"
echo "YARN memory: 3072 MB"
echo "YARN CPU vcores: 2"
echo "Web interfaces are bound to localhost."
echo "Next: validate configuration before formatting NameNode."
