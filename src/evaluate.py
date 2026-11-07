
from pathlib import Path

import numpy as np
import pandas as pd

from src.database import load_config
from src.forecast import load_sales_history, forecast_demand


def evaluate_forecasts():
    config = load_config()
    test_days = config["forecast"]["test_days"]

    print("Loading historical sales...")
    sales = load_sales_history()

    print("Loading ground-truth demand...")
    
    truth = pd.read_parquet(
    "data/ground_truth/daily_demand.parquet"
    )

    # Ground-truth data uses "date"; align it with SalesHistory.
    truth = truth.rename(columns={"date": "sale_date"})

    truth["sale_date"] = pd.to_datetime(truth["sale_date"])


    last_date = sales["sale_date"].max()

    cutoff_date = last_date - pd.Timedelta(days=test_days)

    train = sales[sales["sale_date"] <= cutoff_date].copy()

    test_truth = truth[
        truth["sale_date"] > cutoff_date
    ].copy()

    print(f"Training ends: {cutoff_date.date()}")
    print(f"Test period starts: {(cutoff_date + pd.Timedelta(days=1)).date()}")
    print(f"Test period ends: {last_date.date()}")

    print("Generating backtest forecasts...")
    predictions = forecast_demand(
        train,
        horizon_days=test_days,
    )

    evaluation = predictions.merge(
        test_truth[
            ["store_id", "sku_id", "sale_date", "true_demand"]
        ],
        left_on=["store_id", "sku_id", "forecast_date"],
        right_on=["store_id", "sku_id", "sale_date"],
        how="inner",
        validate="one_to_one",
    )

    if len(evaluation) != len(predictions):
        raise ValueError(
            "Some forecasts have no matching ground-truth demand."
        )

    actual = evaluation["true_demand"].to_numpy(dtype=float)
    predicted = evaluation["predicted_demand"].to_numpy(dtype=float)

    errors = predicted - actual

    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))

    total_actual = np.sum(actual)

    wape = (
        np.sum(np.abs(errors)) / total_actual * 100
        if total_actual > 0
        else np.nan
    )

    bias = np.mean(errors)

    metrics = pd.DataFrame([{
        "model_name": "moving_average_7d",
        "test_days": test_days,
        "forecast_count": len(evaluation),
        "MAE": round(float(mae), 4),
        "RMSE": round(float(rmse), 4),
        "WAPE_percent": round(float(wape), 2),
        "bias": round(float(bias), 4),
    }])

    output_dir = Path("outputs/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "forecast_metrics.csv"
    detail_path = output_dir / "backtest_predictions.csv"

    metrics.to_csv(metrics_path, index=False)
    evaluation.to_csv(detail_path, index=False)

    print("\nForecast accuracy metrics:")
    print(metrics.to_string(index=False))

    print(f"\nMetrics saved to: {metrics_path}")
    print(f"Backtest predictions saved to: {detail_path}")

    return metrics


if __name__ == "__main__":
    evaluate_forecasts()
