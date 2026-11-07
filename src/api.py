
"""REST API for YottaFlex forecasting and replenishment."""

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="YottaFlex Forecasting API",
    description="Demand forecasts and inventory replenishment recommendations.",
    version="1.0.0",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FORECAST_PATH = (
    PROJECT_ROOT / "outputs/forecasts/baseline_forecast.csv"
)

RECOMMENDATION_PATH = (
    PROJECT_ROOT / "outputs/recommendations/replenishment.csv"
)


def read_csv_or_503(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required output is missing: {path.name}",
        )
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to read {path.name}",
        ) from exc


@app.get("/health")
def health():
    return {"status": "ok", "service": "yottaflex-api"}


@app.get("/forecasts")
def get_forecasts(
    store_id: str | None = None,
    sku_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    data = read_csv_or_503(FORECAST_PATH)

    if store_id:
        data = data[data["store_id"] == store_id]

    if sku_id:
        data = data[data["sku_id"] == sku_id]

    return {
        "count": min(len(data), limit),
        "total_matching": len(data),
        "data": data.head(limit).to_dict(orient="records"),
    }


@app.get("/recommendations")
def get_recommendations(
    store_id: str | None = None,
    sku_id: str | None = None,
    priority: str | None = None,
    orders_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
):
    data = read_csv_or_503(RECOMMENDATION_PATH)

    if store_id:
        data = data[data["store_id"] == store_id]

    if sku_id:
        data = data[data["sku_id"] == sku_id]

    if priority:
        data = data[
            data["priority"].str.lower() == priority.lower()
        ]

    if orders_only:
        data = data[data["recommended_qty"] > 0]

    return {
        "count": min(len(data), limit),
        "total_matching": len(data),
        "data": data.head(limit).to_dict(orient="records"),
    }
