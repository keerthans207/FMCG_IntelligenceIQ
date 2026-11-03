# Viva Preparation Guide

Likely technical questions and accurate answers for the academic viva.

## Architecture Questions

**Q: Why use MongoDB instead of a relational database?**
A: FMCG data has varying structures per entity (products, transactions, batches). MongoDB's document model handles schema flexibility naturally. Fast indexed queries support real-time dashboard reads. JSON-native storage aligns with API responses.

**Q: Why HDFS for historical data?**
A: HDFS provides distributed, write-once-read-many storage optimized for batch analytics. It scales horizontally as data grows. Parquet format in HDFS enables columnar reads that Spark processes efficiently.

**Q: Why Spark instead of MapReduce?**
A: Spark uses in-memory processing (RDD/DataFrame caching), making it 10-100x faster than disk-based MapReduce for iterative workloads. The unified API handles ETL, SQL, and ML in one framework. MLlib provides distributed machine learning.

**Q: What is the difference between MongoDB, HDFS, and Spark?**
A: MongoDB is an operational NoSQL database for random read/write access. HDFS is a distributed file system for sequential batch reads. Spark is a distributed processing engine that reads from HDFS and transforms data in memory. They serve different purposes in the pipeline.

## Hadoop Questions

**Q: Why is replication set to 1?**
A: Single-node academic deployment has only one DataNode. Replication=1 means no fault tolerance — if the DataNode fails, data is lost. This is documented and acceptable for academic demonstration. In a multi-node cluster, replication would be 3.

**Q: What are the Hadoop daemons running?**
A: NameNode (metadata management), DataNode (block storage), ResourceManager (YARN job scheduling), NodeManager (YARN task execution).

## Spark Questions

**Q: How does Spark SQL differ from Hive?**
A: Spark SQL uses the Catalyst optimizer and Tungsten execution engine. It operates on DataFrames with native code generation. We do not use Hive — all queries run through Spark SQL's own execution engine.

**Q: How does your MLlib pipeline prevent data leakage?**
A: Train/test split is chronological (80/20 by date, not random). Lag features use F.lag() which only looks backward. Rolling means use rowsBetween(-7, -1) which excludes the current row. The evaluation period never overlaps with training.

**Q: Why Random Forest for demand forecasting?**
A: Random Forest handles non-linear relationships, captures interactions between features (day_of_week, lag, promotion), is robust to outliers, and requires minimal hyperparameter tuning. It serves as a strong baseline candidate for tabular time-series data.

## MongoDB Questions

**Q: How do you prevent duplicate ingestion?**
A: Each collection has a unique index on the business key (e.g., transaction_id). Ingestion uses upsert (update-or-insert) keyed on this identifier. Re-running the pipeline with the same input updates existing records rather than creating duplicates.

**Q: How is current stock calculated?**
A: A snapshot is a point-in-time observation, not a complete history. Current stock is the latest snapshot per location/sku/batch, with available_stock = on_hand - reserved. Snapshots and movements are kept logically separate.

## Anomaly Detection Questions

**Q: How do you detect anomalies?**
A: We use z-score for demand (flagging records where |z| > 2.5) and rule-based checks for inventory (negative balances, large adjustments). Each anomaly includes evidence (mean, std, z-score) so it is explainable.

**Q: Do you label anomalies as fraud?**
A: No. Anomalies indicate statistical outliers or rule violations that warrant investigation. We do not claim fraud detection without supporting evidence.

## Deployment Questions

**Q: Why is everything on a remote server?**
A: The Big Data stack (Hadoop, Spark, MongoDB) requires significant RAM and disk. The developer's Windows laptop has limited SSD space and 4 GB RAM. Running the stack remotely avoids local resource constraints while allowing development via SSH.

**Q: How is the dashboard accessed?**
A: Via SSH tunnel. MongoDB and HDFS management ports are not exposed publicly. The SSH tunnel forwards the Streamlit and FastAPI ports to localhost on the developer's machine.
