#!/usr/bin/env python3
"""
Spark Job 7: Demand Forecasting with Spark MLlib

Predicts daily product demand for each SKU and location over the
next 7 days using historical sales records.

Implements:
- Feature engineering: temporal features, lag features, rolling means
- Chronological train/test split (prevents data leakage)
- Linear Regression baseline model
- Random Forest Regression primary model
- Evaluation: MAE, RMSE, MAPE
- 7-day prediction generation
- Model persistence

Uses StringIndexer + OneHotEncoder for categoricals and VectorAssembler
for the feature vector, all within a Spark ML Pipeline.
"""

from __future__ import annotations

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fmcg.analytics.spark_session import create_spark_session, get_hdfs_base_path
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType
from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    StringIndexer, OneHotEncoder, VectorAssembler,
)
from pyspark.ml.regression import (
    LinearRegression, RandomForestRegressor,
)
from pyspark.ml.evaluation import RegressionEvaluator


FORECAST_HORIZON_DAYS = 7


def build_features(sales_df):
    """
    Build feature columns for demand forecasting.

    Features:
    - day_of_week (1-7)
    - month (1-12)
    - is_weekend (0/1)
    - lag_1, lag_7, lag_14 (demand from 1, 7, 14 days ago)
    - rolling_mean_7, rolling_mean_14 (trailing averages, excl. current day)
    - promotion_flag
    """
    # Aggregate to daily level per sku/location
    daily = sales_df.groupBy(
        "transaction_date",
        F.col("sku_id"),
        F.col("store_id").alias("location_id"),
    ).agg(
        F.sum("units_sold").alias("demand"),
        F.max("promotion_flag").alias("promotion_flag"),
    )

    # Sort by date for window functions
    w = Window.partitionBy("sku_id", "location_id").orderBy("transaction_date")

    # Temporal features
    daily = daily.withColumn("day_of_week", F.dayofweek("transaction_date"))
    daily = daily.withColumn("month", F.month("transaction_date"))
    daily = daily.withColumn("is_weekend",
        F.when(F.dayofweek("transaction_date").isin([1, 7]), 1).otherwise(0))

    # Lag features (using lag window function — only past data)
    daily = daily.withColumn("lag_1", F.lag("demand", 1).over(w))
    daily = daily.withColumn("lag_7", F.lag("demand", 7).over(w))
    daily = daily.withColumn("lag_14", F.lag("demand", 14).over(w))

    # Rolling mean (trailing, excluding current day via rowsBetween)
    daily = daily.withColumn("rolling_mean_7",
        F.avg("demand").over(w.rowsBetween(-7, -1)))
    daily = daily.withColumn("rolling_mean_14",
        F.avg("demand").over(w.rowsBetween(-14, -1)))

    # Fill null lags/rolling with 0 (insufficient history)
    daily = daily.fillna(0, subset=["lag_1", "lag_7", "lag_14",
                                     "rolling_mean_7", "rolling_mean_14"])

    return daily


def train_and_evaluate(spark, daily_df, model_dir: str):
    """
    Train models with chronological split and evaluate.

    Chronological split: last 20% of dates are test data (no random split).
    """
    # Determine split date (80/20 chronological)
    date_count = daily_df.select("transaction_date").distinct().count()
    split_idx = int(date_count * 0.8)
    dates = [row.transaction_date for row in
             daily_df.select("transaction_date").distinct()
             .orderBy("transaction_date").collect()]
    split_date = dates[split_idx]

    print(f"  Train: dates before {split_date}")
    print(f"  Test:  dates from {split_date} onwards")

    train_df = daily_df.filter(F.col("transaction_date") < split_date)
    test_df = daily_df.filter(F.col("transaction_date") >= split_date)

    train_count = train_df.count()
    test_count = test_df.count()
    print(f"  Train records: {train_count:,}")
    print(f"  Test records:  {test_count:,}")

    # --- Build ML Pipeline ---

    # Index categorical features
    sku_indexer = StringIndexer(inputCol="sku_id", outputCol="sku_idx",
                                handleInvalid="keep")
    loc_indexer = StringIndexer(inputCol="location_id", outputCol="loc_idx",
                                 handleInvalid="keep")

    # One-hot encode
    encoder = OneHotEncoder(
        inputCols=["sku_idx", "loc_idx"],
        outputCols=["sku_vec", "loc_vec"],
    )

    # Assemble feature vector
    feature_cols = [
        "sku_vec", "loc_vec", "day_of_week", "month", "is_weekend",
        "lag_1", "lag_7", "lag_14",
        "rolling_mean_7", "rolling_mean_14", "promotion_flag",
    ]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features",
                                handleInvalid="keep")

    # --- Model 1: Linear Regression (baseline) ---
    print("\n  Training Linear Regression (baseline)...")
    lr = LinearRegression(
        featuresCol="features",
        labelCol="demand",
        maxIter=50,
        regParam=0.1,
    )
    lr_pipeline = Pipeline(stages=[sku_indexer, loc_indexer, encoder, assembler, lr])
    lr_model = lr_pipeline.fit(train_df)
    lr_predictions = lr_model.transform(test_df)

    # --- Model 2: Random Forest Regression ---
    print("  Training Random Forest Regression...")
    rf = RandomForestRegressor(
        featuresCol="features",
        labelCol="demand",
        numTrees=30,
        maxDepth=10,
        seed=42,
    )
    rf_pipeline = Pipeline(stages=[sku_indexer, loc_indexer, encoder, assembler, rf])
    rf_model = rf_pipeline.fit(train_df)
    rf_predictions = rf_model.transform(test_df)

    # --- Evaluate ---
    mae_eval = RegressionEvaluator(labelCol="demand", predictionCol="prediction",
                                    metricName="mae")
    rmse_eval = RegressionEvaluator(labelCol="demand", predictionCol="prediction",
                                     metricName="rmse")

    lr_mae = mae_eval.evaluate(lr_predictions)
    lr_rmse = rmse_eval.evaluate(lr_predictions)
    rf_mae = mae_eval.evaluate(rf_predictions)
    rf_rmse = rmse_eval.evaluate(rf_predictions)

    print(f"\n  === Evaluation Results ===")
    print(f"  Linear Regression:  MAE={lr_mae:.4f}  RMSE={lr_rmse:.4f}")
    print(f"  Random Forest:      MAE={rf_mae:.4f}  RMSE={rf_rmse:.4f}")

    # --- Baseline: historical average ---
    print("  Computing baseline (historical average)...")
    train_avg = train_df.groupBy("sku_id", "location_id").agg(
        F.avg("demand").alias("baseline_prediction")
    )
    baseline_pred = test_df.join(train_avg, ["sku_id", "location_id"], "left"
    ).fillna(0, subset=["baseline_prediction"])
    baseline_mae = mae_eval.evaluate(
        baseline_pred.withColumnRenamed("baseline_prediction", "prediction")
    )
    baseline_rmse = rmse_eval.evaluate(
        baseline_pred.withColumnRenamed("baseline_prediction", "prediction")
    )
    print(f"  Baseline (avg):      MAE={baseline_mae:.4f}  RMSE={baseline_rmse:.4f}")

    # Determine best model
    best_model = rf_model if rf_mae < lr_mae else lr_model
    best_name = "random_forest" if rf_mae < lr_mae else "linear_regression"
    best_mae = min(rf_mae, lr_mae)
    best_rmse = min(rf_rmse, lr_rmse)
    model_better = best_mae < baseline_mae

    print(f"\n  Best model: {best_name}")
    print(f"  Model better than baseline: {model_better}")

    # --- Save model ---
    model_path = f"{model_dir}/demand_forecast_{best_name}"
    best_model.write().overwrite().save(model_path)
    print(f"  Model saved to: {model_path}")

    # --- Save evaluation metrics ---
    metrics = {
        "linear_regression": {"mae": float(lr_mae), "rmse": float(lr_rmse)},
        "random_forest": {"mae": float(rf_mae), "rmse": float(rf_rmse)},
        "baseline": {"mae": float(baseline_mae), "rmse": float(baseline_rmse)},
        "best_model": best_name,
        "model_better_than_baseline": model_better,
        "split_date": str(split_date),
        "train_records": train_count,
        "test_records": test_count,
    }

    return best_model, metrics, rf_predictions


def generate_predictions(best_model, daily_df, hdfs_base: str):
    """Generate 7-day demand predictions for each SKU/location."""

    print("\n  Generating 7-day forecasts...")
    max_date = daily_df.select(F.max("transaction_date")).collect()[0][0]
    if max_date is None:
        print("  No data available for forecasting.")
        return None

    # Get unique sku/location combinations
    combos = daily_df.select("sku_id", "location_id").distinct()
    combos_list = [(row.sku_id, row.location_id) for row in combos.collect()]

    if not combos_list:
        print("  No SKU/location combinations found.")
        return None

    # Generate prediction rows for next 7 days
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType, DateType, BooleanType,
    )

    pred_schema = StructType([
        StructField("transaction_date", DateType(), False),
        StructField("sku_id", StringType(), False),
        StructField("location_id", StringType(), False),
        StructField("day_of_week", IntegerType(), False),
        StructField("month", IntegerType(), False),
        StructField("is_weekend", IntegerType(), False),
        StructField("lag_1", DoubleType(), True),
        StructField("lag_7", DoubleType(), True),
        StructField("lag_14", DoubleType(), True),
        StructField("rolling_mean_7", DoubleType(), True),
        StructField("rolling_mean_14", DoubleType(), True),
        StructField("promotion_flag", BooleanType(), True),
        StructField("demand", DoubleType(), True),
    ])

    pred_rows = []
    start_date = max_date + timedelta(days=1)
    for sku, loc in combos_list:
        for d in range(FORECAST_HORIZON_DAYS):
            pred_date = start_date + timedelta(days=d)
            # Use lag features from last known values
            last_records = (daily_df
                .filter((F.col("sku_id") == sku) & (F.col("location_id") == loc))
                .orderBy(F.col("transaction_date").desc())
                .limit(15)
                .collect())

            lag_1 = last_records[0].demand if len(last_records) > 0 else 0.0
            lag_7 = last_records[6].demand if len(last_records) > 6 else 0.0
            lag_14 = last_records[13].demand if len(last_records) > 13 else 0.0

            recent_7 = [r.demand for r in last_records[:7][::-1]]
            rolling_7 = sum(recent_7) / len(recent_7) if recent_7 else 0.0
            recent_14 = [r.demand for r in last_records[:14][::-1]]
            rolling_14 = sum(recent_14) / len(recent_14) if recent_14 else 0.0

            pred_rows.append((
                pred_date, sku, loc,
                pred_date.isoweekday(), pred_date.month,
                1 if pred_date.isoweekday() >= 6 else 0,
                float(lag_1), float(lag_7), float(lag_14),
                float(rolling_7), float(rolling_14),
                False, 0.0,  # promotion_flag, demand (unknown for future)
            ))

    pred_df = spark.createDataFrame(pred_rows, schema=pred_schema)
    predictions = best_model.transform(pred_df)
    predictions = predictions.withColumn("predicted_units",
        F.round(F.when(F.col("prediction") < 0, 0.0).otherwise(F.col("prediction")), 2)
    ).withColumnRenamed("transaction_date", "forecast_date")

    result = predictions.select(
        "forecast_date", "sku_id", "location_id", "predicted_units"
    ).orderBy("sku_id", "location_id", "forecast_date")

    result.write.mode("overwrite").parquet(f"{hdfs_base}/forecasts/predictions/daily_predictions")
    pred_count = result.count()
    print(f"  Generated {pred_count:,} forecast records ({FORECAST_HORIZON_DAYS} days)")
    return result


def run_demand_forecasting(spark, hdfs_base: str, model_dir: str = "/data/fmcg/models"):
    """Main entry point for demand forecasting."""

    print("Loading sales data...")
    sales = spark.read.parquet(f"{hdfs_base}/silver/cleaned_sales")

    print("Building features...")
    daily_df = build_features(sales)

    print("Training and evaluating models...")
    best_model, metrics, predictions = train_and_evaluate(spark, daily_df, model_dir)

    print("Generating 7-day predictions...")
    forecast_result = generate_predictions(best_model, daily_df, hdfs_base)

    # Save metrics to HDFS
    import json
    metrics_json = json.dumps(metrics, indent=2, default=str)
    spark.sparkContext.parallelize([metrics_json]).saveAsTextFile(
        f"{hdfs_base}/forecasts/evaluation/latest_metrics"
    )

    print("\n=== Demand Forecasting Summary ===")
    for model_name, model_metrics in metrics.items():
        if isinstance(model_metrics, dict) and "mae" in model_metrics:
            print(f"  {model_name:20s}  MAE={model_metrics['mae']:.4f}  RMSE={model_metrics['rmse']:.4f}")
    print(f"  Best model: {metrics.get('best_model', 'N/A')}")
    print(f"  Better than baseline: {metrics.get('model_better_than_baseline', 'N/A')}")

    return metrics


if __name__ == "__main__":
    spark = create_spark_session(app_name="FMCG-DemandForecasting")
    hdfs_base = get_hdfs_base_path()
    model_dir = os.environ.get("MODEL_DIR", "/data/fmcg/models")
    try:
        metrics = run_demand_forecasting(spark, hdfs_base, model_dir)
        print("\nDemand forecasting completed successfully.")
    except Exception as e:
        print(f"\nDemand forecasting FAILED: {e}")
        raise
    finally:
        spark.stop()
