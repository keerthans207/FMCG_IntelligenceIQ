# Testing Strategy

## Test Pyramid

```
        ┌───────────────┐
        │  End-to-End    │  Requires full remote stack
        │  (7 tests)     │  MongoDB + HDFS + Spark
        └───────┬────────┘
        ┌───────▼────────┐
        │  Integration   │  Require MongoDB or Spark
        │  (4 tests)     │  Skip if services unavailable
        └───────┬────────┘
    ┌───────────▼────────────┐
    │     Unit Tests          │  Pure Python, no deps
    │     (94 tests)          │  Run locally on Windows
    └────────────────────────┘
```

## Running Tests

### Unit Tests (local, no dependencies)
```bash
python -m pytest tests/unit/ -v
```
Result: 94 tests covering schema validation, duplicate detection, inventory calculations, days of stock remaining, reorder recommendations, expiry categorization, FEFO ranking, shipment delays, anomaly detection, forecast feature engineering, evaluation metrics, and data generator reproducibility.

### Integration Tests (require remote services)
```bash
python -m pytest tests/integration/ -m integration -v
```
Tests MongoDB connection, idempotent writes, Spark DataFrame operations, and Spark SQL queries. Skipped automatically if services are unavailable.

### End-to-End Tests (require full remote stack)
```bash
python -m pytest tests/end_to_end/ -m integration -v
```
Tests the complete pipeline: data generation → MongoDB ingestion → HDFS storage → Spark processing → SQL analytics → MLlib training → API → dashboard → rerun without duplicates.

## Test Markers

- `@pytest.mark.unit` — lightweight, no external services
- `@pytest.mark.integration` — requires MongoDB/HDFS/Spark
- `@pytest.mark.slow` — takes more than a few seconds

## What Is NOT Tested

- Never report an unexecuted test as passing.
- Integration tests skip (not fail) when services are unavailable.
- Performance benchmarks record actual measurements — no fabricated numbers.
- Forecast accuracy is reported honestly even if the model performs worse than baseline.
