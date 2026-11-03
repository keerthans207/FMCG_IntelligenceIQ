# Problem Statement

## Domain

FMCG (Fast-Moving Consumer Goods) companies distribute products through a supply chain involving manufacturers, warehouses, distributors, wholesalers, and retail stores. Large volumes of sales, inventory, batch, shipment, and stock movement data are generated daily.

## Current Challenges

Without integrated analytics, FMCG businesses face:

- **Unexpected stockouts**: Products go out of stock without warning, causing lost sales.
- **Excess inventory**: Overstocking ties up capital and increases storage costs.
- **Expiry-related losses**: Products expire before sale when batches aren't managed with FEFO.
- **Unbalanced stock distribution**: Stock is in the wrong location, creating artificial shortages.
- **Shipment delays**: Delivery timelines slip without early warning.
- **Poor demand forecasting**: Replenishment decisions rely on intuition rather than data.
- **Unusual inventory movements**: Stock adjustments and anomalies go undetected.
- **Inefficient replenishment**: Orders are placed too late or in wrong quantities.

## Proposed Solution

A Big Data intelligence platform that consolidates these data sources and processes them through:

1. **MongoDB** — NoSQL operational database for real-time queries
2. **Hadoop HDFS** — Distributed data lake for historical storage
3. **Apache Spark** — Distributed processing, Spark SQL, and MLlib for forecasting

The platform provides inventory health monitoring, expiry risk analysis, supply chain analytics, anomaly detection, and demand forecasting — enabling data-driven replenishment decisions.
