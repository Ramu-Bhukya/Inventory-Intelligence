
import pandas as pd

from src.database import get_connection, load_config


def load_sales_history():
    con = get_connection()

    try:
        sales = con.execute("""
            SELECT
                store_id,
                sku_id,
                sale_date,
                units_sold,
                stockout_flag
            FROM SalesHistory
            ORDER BY store_id, sku_id, sale_date
        """).df()
    finally:
        con.close()

    sales["sale_date"] = pd.to_datetime(sales["sale_date"])

    return sales


def forecast_demand(sales, horizon_days=14, window_days=7):
    forecasts = []

    for (store_id, sku_id), group in sales.groupby(
        ["store_id", "sku_id"]
    ):
        group = group.sort_values("sale_date")

        recent = group.tail(window_days)

        available = recent[
            recent["stockout_flag"] == 0
        ]

        if available.empty:
            available = group[
                group["stockout_flag"] == 0
            ].tail(28)

        if available.empty:
            predicted_daily_demand = 0.0
        else:
            predicted_daily_demand = float(
                available["units_sold"].mean()
            )

        last_date = group["sale_date"].max()

        for day in range(1, horizon_days + 1):
            forecasts.append({
                "store_id": store_id,
                "sku_id": sku_id,
                "forecast_date": last_date
                + pd.Timedelta(days=day),
                "predicted_demand": round(
                    predicted_daily_demand, 2
                ),
                "model_name": "moving_average_7d",
            })

    return pd.DataFrame(forecasts)


def main():
    config = load_config()

    horizon_days = config["forecast"]["horizon_days"]

    print("Loading sales history...")
    sales = load_sales_history()

    print("Generating demand forecasts...")
    forecasts = forecast_demand(
        sales,
        horizon_days=horizon_days,
    )

    output_path = "outputs/forecasts/baseline_forecast.csv"

    forecasts.to_csv(output_path, index=False)

    print(f"Forecast rows: {len(forecasts)}")
    print(f"Forecast saved to: {output_path}")

    print(forecasts.head())


if __name__ == "__main__":
    main()
