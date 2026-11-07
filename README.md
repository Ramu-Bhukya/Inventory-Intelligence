# YottaFlex Inventory Intelligence

An end-to-end proof of concept for demand forecasting, inventory risk analysis, and supplier-aware replenishment recommendations.

The project demonstrates a forward-deployed engineering workflow: generating and validating retail data, forecasting SKU-level demand, evaluating model performance, producing purchase recommendations, and exposing results through an interactive dashboard and REST API.

## Features

- Synthetic retail dataset with 50 SKUs, 5 stores, and 10 suppliers
- 90 days of historical sales and inventory observations
- Stockout-aware baseline demand forecasting
- 14-day demand forecasts for each SKU-store combination
- Backtesting against synthetic ground-truth demand
- Supplier-aware replenishment recommendations
- Safety stock, reorder point, and target inventory calculations
- Pack-size and minimum-order-quantity constraints
- Interactive Streamlit dashboard
- FastAPI endpoints for forecasts and recommendations
- DuckDB analytical database
- Data validation and automated tests
- Docker and Docker Compose support

## Technology Stack

Python 3.12, pandas, NumPy, DuckDB, SciPy, PyArrow, Streamlit, Altair, FastAPI, Uvicorn, pytest, and Docker.

## Project Structure

```text
yottaflex-forecast/
├── config/
│   └── settings.yaml
├── dashboard/
│   └── app.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── ground_truth/
├── docs/
│   ├── schema.sql
│   ├── data_dictionary.csv
│   ├── assumptions.md
│   └── source_manifest.json
├── outputs/
│   ├── forecasts/
│   ├── recommendations/
│   └── reports/
├── src/
│   ├── api.py
│   ├── database.py
│   ├── evaluate.py
│   ├── forecast.py
│   ├── generate_data.py
│   ├── replenishment.py
│   └── validate_data.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Local Installation

Clone the repository and open a terminal in the project directory.

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run all commands below from the project root.

## Generate and Validate Data

Initialize the DuckDB database:

```bash
python -m src.database
```

Generate the synthetic dataset:

```bash
python -m src.generate_data
```

Validate data integrity:

```bash
python -m src.validate_data
```

The generated data includes sales history, inventory snapshots, supplier relationships, lead-time observations, and ground-truth customer demand.

## Forecast Demand

Generate the baseline demand forecast:

```bash
python -m src.forecast
```

The forecast horizon is 14 days. The baseline estimates demand using recent non-stockout sales observations to reduce the effect of censored demand.

Forecast output:

`outputs/forecasts/baseline_forecast.csv`

## Evaluate Forecast Accuracy

Run the historical backtest:

```bash
python -m src.evaluate
```

The evaluation compares predictions against synthetic ground-truth demand and reports:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Weighted Absolute Percentage Error (WAPE)
- Forecast bias

Evaluation files are written to `outputs/reports/`.

## Generate Replenishment Recommendations

Run:

```bash
python -m src.replenishment
```

The replenishment model uses demand forecasts, inventory position, supplier lead times, safety stock, service-level assumptions, review periods, minimum order quantities, and pack sizes.

Output:

`outputs/recommendations/replenishment.csv`

Recommendations are planning estimates, not automatically approved purchase orders.

## Launch the Streamlit Dashboard

```bash
python -m streamlit run dashboard/app.py
```

Open:

http://localhost:8501

The dashboard includes executive KPIs, forecast accuracy, SKU-level demand forecasts, historical sales and stockout visualization, inventory risk analysis, and purchase recommendations.

## Launch the FastAPI Service

Open another terminal and run:

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Interactive API documentation:

http://127.0.0.1:8000/docs

Available endpoints:

- `GET /health`
- `GET /forecasts`
- `GET /recommendations`

The forecast and recommendation endpoints support filtering by store and SKU. Recommendations additionally support priority and order-only filters.

Example:

```text
http://127.0.0.1:8000/forecasts?store_id=STORE001&sku_id=SKU00001&limit=14
```

## Docker Deployment

The Docker image packages the application and its dependencies.

Build:

```bash
docker compose build
```

Start:

```bash
docker compose up -d
```

Open:

http://localhost:8501

Check container status:

```bash
docker compose ps
```

Stop:

```bash
docker compose down
```

**Important:** The current Docker configuration expects the generated database and output files to exist before building. Run the data generation, forecasting, evaluation, and replenishment steps first.

The `data/` and `outputs/` artifacts are excluded from Git. A fresh clone therefore requires the generation pipeline before the Docker build.

## Automated Tests

Run the complete test suite:

```bash
python -m pytest -v
```

Tests cover data integrity, forecasting, replenishment calculations, supplier constraints, and reproducibility.

## Baseline Results

The current synthetic dataset produced the following results:

| Metric | Result |
|---|---:|
| SKU-store combinations | 250 |
| Forecast horizon | 14 days |
| Forecast predictions | 3,500 |
| Forecast MAE | 4.05 units |
| Forecast RMSE | 5.37 units |
| Forecast WAPE | 33.68% |
| Purchase recommendations | 138 |
| Recommended units | 30,288 |
| Estimated purchase cost | $1,629,936.54 |
| Critical purchase recommendations | 82 |

These results are specific to the seeded synthetic dataset and baseline modeling assumptions. They are not claims of production forecasting accuracy.

## Assumptions and Limitations

- The dataset is synthetic and does not contain real retailer transactions.
- The baseline forecast uses recent historical sales rather than a fully trained machine-learning model.
- Stockouts can censor observed sales, so historical sales may understate true demand.
- Replenishment calculations approximate demand and lead-time uncertainty.
- Incoming purchase orders are included in inventory position without modeling their exact arrival dates.
- Supplier constraints are applied, but the system does not automatically place purchase orders.
- The Streamlit dashboard currently reads generated CSV files and DuckDB directly rather than consuming the FastAPI endpoints.

## Future Improvements

Potential next steps include production data connectors, richer forecasting models, demand uncertainty calibration, supplier lead-time monitoring, arrival-aware inventory planning, and scheduled forecast refreshes.

## Disclaimer

This is a proof-of-concept inventory decision-support system. Forecasts and purchasing recommendations should be reviewed before operational use.
