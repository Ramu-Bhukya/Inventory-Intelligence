
import pandas as pd

from src.database import load_config
from src.forecast import load_sales_history, forecast_demand


def test_forecast_row_count():
    config = load_config()
    sales = load_sales_history()

    forecasts = forecast_demand(
        sales,
        horizon_days=config["forecast"]["horizon_days"],
    )

    expected = (
        config["data_generation"]["sku_count"]
        * config["data_generation"]["store_count"]
        * config["forecast"]["horizon_days"]
    )

    assert len(forecasts) == expected


def test_no_negative_forecasts():
    sales = load_sales_history()
    forecasts = forecast_demand(sales)

    assert (
        forecasts["predicted_demand"] >= 0
    ).all()


def test_no_missing_forecasts():
    sales = load_sales_history()
    forecasts = forecast_demand(sales)

    assert forecasts["predicted_demand"].notna().all()
    assert forecasts["forecast_date"].notna().all()


def test_forecasts_start_after_history():
    sales = load_sales_history()
    forecasts = forecast_demand(sales)

    last_history_date = pd.to_datetime(
        sales["sale_date"]
    ).max()

    first_forecast_date = pd.to_datetime(
        forecasts["forecast_date"]
    ).min()

    assert first_forecast_date > last_history_date


def test_forecast_file_exists():
    forecasts = pd.read_csv(
        "outputs/forecasts/baseline_forecast.csv"
    )

    assert not forecasts.empty
    assert len(forecasts) == 3500


def test_backtest_metrics():
    import numpy as np
    import pandas as pd

    metrics = pd.read_csv(
        "outputs/reports/forecast_metrics.csv"
    )

    predictions = pd.read_csv(
        "outputs/reports/backtest_predictions.csv"
    )

    assert len(metrics) == 1
    assert len(predictions) == 3500

    assert predictions["true_demand"].notna().all()
    assert predictions["predicted_demand"].notna().all()

    actual = predictions["true_demand"].to_numpy(dtype=float)
    forecast = predictions["predicted_demand"].to_numpy(dtype=float)

    errors = forecast - actual

    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))
    bias = np.mean(errors)

    assert np.isclose(metrics.loc[0, "MAE"], mae, atol=0.0001)
    assert np.isclose(metrics.loc[0, "RMSE"], rmse, atol=0.0001)
    assert np.isclose(metrics.loc[0, "bias"], bias, atol=0.0001)

    assert metrics.loc[0, "forecast_count"] == len(predictions)
