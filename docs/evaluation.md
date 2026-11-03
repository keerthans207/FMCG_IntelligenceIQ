# Evaluation

## Data Processing Performance

Metrics measured across dataset sizes (10K, 100K, 500K, 1M records):

| Metric | Description |
|---|---|
| Data ingestion duration | Time to write records to MongoDB |
| HDFS storage time | Time to upload and store in HDFS |
| Spark transformation duration | Time for ETL + analytics jobs |
| Spark SQL execution duration | Time for analytical queries |
| Forecast training duration | Time to train MLlib model |
| Total execution duration | End-to-end pipeline time |
| Throughput | Records per second |
| Invalid record count | Records rejected by validation |

Run: `python scripts/pipeline/benchmark.py`

**Important**: All measurements are actual. No fabricated numbers. Single-node results do not claim multi-node scalability.

## Forecasting Accuracy

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Square Error |
| MAPE | Mean Absolute Percentage Error (where defined) |
| Baseline MAE | Historical-average baseline for comparison |

The ML model (Random Forest) is compared against a simple historical-average baseline. If the model performs worse than the baseline, that is reported honestly.

### Data Leakage Prevention

- Train/test split is chronological (last 20% of dates as test).
- Lag features use only past data (never future).
- Rolling means exclude the current day.
- Evaluation period is separate from training.

## Inventory Calculations

Verified by 94 unit tests:
- Available stock = on_hand - reserved
- Days remaining = available / avg_daily_demand (None if no demand)
- Reorder quantity with safety stock, incoming stock, min order, reorder multiples
- Stockout risk classification (critical/high/medium/low/none)
- FEFO ranking by expiry date
- Expiry classification (expired/critical/approaching/healthy)
- Shipment delay detection (delivered vs expected vs overdue)
- Anomaly detection via z-score with evidence

## What Is NOT Claimed

- Multi-node distributed performance from single-node experiments
- Fault tolerance from replication=1
- Fraud detection from statistical anomaly flags
- 100% forecast accuracy
