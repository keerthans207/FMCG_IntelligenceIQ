# Project Objectives

1. Design a NoSQL operational database using MongoDB for FMCG data.
2. Implement distributed historical data storage through Hadoop HDFS.
3. Develop an ingestion pipeline for FMCG operational and historical records.
4. Process large datasets using Apache Spark DataFrames and Spark SQL.
5. Perform analytical queries using Spark SQL (sales, inventory, expiry, shipments).
6. Implement demand forecasting using Spark MLlib (Random Forest Regression).
7. Detect inventory, expiry, and supply-chain anomalies using statistical methods.
8. Generate automated stockout and replenishment alerts with recommendations.
9. Provide a dashboard for supply-chain monitoring via Streamlit.
10. Evaluate data processing performance and forecasting accuracy with real metrics.

## Success Criteria

- MongoDB stores operational records with indexes and validation.
- HDFS stores datasets in a medallion architecture (raw → bronze → silver → gold).
- Spark reads from HDFS, transforms data, and writes curated outputs.
- Spark SQL executes 10 analytical queries correctly.
- MLlib trains a real model evaluated with MAE/RMSE against a baseline.
- Anomaly detection flags demand spikes/drops and inventory issues.
- Alerts include descriptions, recommendations, and evidence.
- FastAPI exposes 14 endpoints reading actual MongoDB data.
- Streamlit displays 7 pages with real data, empty states, and error handling.
- Pipeline is idempotent — reruns don't create duplicates.
- Unit tests (94) pass locally; integration tests pass when services run.
- Performance benchmarks record actual measurements (not fabricated).
