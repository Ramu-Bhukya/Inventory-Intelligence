
# from pathlib import Path

# import pandas as pd
# import streamlit as st

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from src.database import get_connection



PROJECT_ROOT = Path(__file__).resolve().parent.parent

RECOMMENDATIONS_PATH = (
    PROJECT_ROOT
    / "outputs/recommendations/replenishment.csv"
)

METRICS_PATH = (
    PROJECT_ROOT
    / "outputs/reports/forecast_metrics.csv"
)


st.set_page_config(
    page_title="YottaFlex Inventory Intelligence",
    page_icon="📦",
    layout="wide",
)


@st.cache_data
def load_data():
    recommendations = pd.read_csv(RECOMMENDATIONS_PATH)
    metrics = pd.read_csv(METRICS_PATH)

    return recommendations, metrics


st.title("YottaFlex Inventory Intelligence")
st.caption(
    "AI-assisted demand forecasting and inventory replenishment"
)

if not RECOMMENDATIONS_PATH.exists() or not METRICS_PATH.exists():
    st.error(
        "Required output files are missing. "
        "Run the forecasting, evaluation, and replenishment scripts."
    )
    st.stop()

recommendations, metrics = load_data()

st.sidebar.header("Filters")

store_options = ["All"] + sorted(
    recommendations["store_id"].unique().tolist()
)

selected_store = st.sidebar.selectbox(
    "Store",
    store_options,
)

priority_options = [
    "All",
    "Critical",
    "High",
    "Normal",
]

selected_priority = st.sidebar.selectbox(
    "Priority",
    priority_options,
)

filtered = recommendations.copy()

if selected_store != "All":
    filtered = filtered[
        filtered["store_id"] == selected_store
    ]

if selected_priority != "All":
    filtered = filtered[
        filtered["priority"] == selected_priority
    ]

orders = filtered[
    filtered["recommended_qty"] > 0
]

st.subheader("Executive Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Purchase Recommendations",
    f"{len(orders):,}",
)

col2.metric(
    "Recommended Units",
    f"{orders['recommended_qty'].sum():,.0f}",
)

col3.metric(
    "Estimated Purchase Cost",
    f"${orders['estimated_order_cost'].sum():,.2f}",
)

col4.metric(
    "Critical Orders",
    f"{(orders['priority'] == 'Critical').sum():,}",
)

st.divider()

st.subheader("Purchase Order Priorities")

priority_counts = (
    orders["priority"]
    .value_counts()
    .reindex(["Critical", "High", "Normal"], fill_value=0)
)

st.bar_chart(priority_counts)

st.divider()

st.subheader("Forecast Model Performance")

metric = metrics.iloc[0]

m1, m2, m3, m4 = st.columns(4)

m1.metric("MAE", f"{metric['MAE']:.2f}")
m2.metric("RMSE", f"{metric['RMSE']:.2f}")
m3.metric("WAPE", f"{metric['WAPE_percent']:.2f}%")
m4.metric("Forecast Bias", f"{metric['bias']:.2f}")

st.divider()

st.subheader("Replenishment Recommendations")

st.dataframe(
    orders.sort_values(
        ["priority", "estimated_order_cost"],
        ascending=[True, False],
    ),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download Purchase Recommendations",
    data=orders.to_csv(index=False),
    file_name="yottaflex_purchase_recommendations.csv",
    mime="text/csv",
)


st.divider()

st.subheader("14-Day Demand Forecast")

FORECAST_PATH = (
    PROJECT_ROOT
    / "outputs/forecasts/baseline_forecast.csv"
)

if FORECAST_PATH.exists():
    forecasts = pd.read_csv(FORECAST_PATH)
    forecasts["forecast_date"] = pd.to_datetime(
        forecasts["forecast_date"]
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        forecast_store = st.selectbox(
            "Select Store",
            sorted(forecasts["store_id"].unique()),
        )

    with chart_col2:
        forecast_sku = st.selectbox(
            "Select SKU",
            sorted(forecasts["sku_id"].unique()),
        )

    selected_forecast = forecasts[
        (forecasts["store_id"] == forecast_store)
        & (forecasts["sku_id"] == forecast_sku)
    ].sort_values("forecast_date")

    if not selected_forecast.empty:
        st.line_chart(
            selected_forecast.set_index("forecast_date")[
                "predicted_demand"
            ]
        )

        st.metric(
            "Total Forecasted Demand (14 Days)",
            f"{selected_forecast['predicted_demand'].sum():,.1f} units",
        )

        st.subheader("Historical Sales vs. Forecast")

        from src.database import get_connection

        con = get_connection()

        try:
            history = con.execute(
                """
                SELECT sale_date, units_sold, stockout_flag
                FROM SalesHistory
                WHERE store_id = ?
                  AND sku_id = ?
                ORDER BY sale_date DESC
                LIMIT 30
                """,
                [forecast_store, forecast_sku],
            ).df()
        finally:
            con.close()

        history["sale_date"] = pd.to_datetime(
            history["sale_date"]
        )

        history = history.sort_values("sale_date")

        historical_series = (
            history[["sale_date", "units_sold"]]
            .rename(
                columns={
                    "sale_date": "date",
                    "units_sold": "Observed Sales",
                }
            )
            .set_index("date")
        )

        forecast_series = (
            selected_forecast[
                ["forecast_date", "predicted_demand"]
            ]
            .rename(
                columns={
                    "forecast_date": "date",
                    "predicted_demand": "Forecast Demand",
                }
            )
            .set_index("date")
        )

        comparison = historical_series.join(
            forecast_series,
            how="outer",
        )

        # st.line_chart(comparison)

        # stockout_days = int(
        #     history["stockout_flag"].sum()
        # )

        # Mark stockout days on the historical sales chart.
        stockout_dates = history[
            history["stockout_flag"] == True
        ].copy()

        stockout_dates["sale_date"] = pd.to_datetime(
            stockout_dates["sale_date"]
        )

        stockout_dates = stockout_dates.rename(
            columns={
                "sale_date": "date",
                "units_sold": "Observed Sales",
            }
        )

        stockout_dates["Stockout"] = stockout_dates[
            "Observed Sales"
        ]

        stockout_markers = (
            stockout_dates[["date", "Stockout"]]
            .set_index("date")
        )

        # Combine historical sales, forecast, and stockout markers.
        chart_data = comparison.join(
            stockout_markers,
            how="left",
        ).reset_index()

        import altair as alt

        lines = alt.Chart(chart_data).transform_fold(
            ["Observed Sales", "Forecast Demand"],
            as_=["Series", "Units"],
        ).mark_line(strokeWidth=2).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("Units:Q", title="Units"),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Observed Sales", "Forecast Demand"],
                    range=["#78BDF2", "#1565C0"],
                ),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("Series:N"),
                alt.Tooltip("Units:Q", format=".1f"),
            ],
        )

        markers = alt.Chart(
            chart_data.dropna(subset=["Stockout"])
        ).mark_circle(
            size=110,
            color="#E53935",
        ).encode(
            x="date:T",
            y="Stockout:Q",
            tooltip=[
                alt.Tooltip("date:T", title="Stockout Date"),
                alt.Tooltip("Stockout:Q", title="Observed Sales"),
            ],
        )

        st.altair_chart(
            lines + markers,
            use_container_width=True,
        )

        stockout_days = len(stockout_dates)


        st.caption(
            f"Historical period includes {stockout_days} "
            "stockout days. Observed sales may understate "
            "true customer demand during stockouts."
        )

    else:
        st.warning("No forecast found for this SKU-store pair.")
else:
    st.warning("Forecast file not found.")

st.caption(
    "Recommendations are planning estimates, not approved "
    "purchase orders. Priority is based on inventory position "
    "and does not yet account for incoming order arrival dates."
)

# --------------------------------------------------
# SKU-Level Inventory Risk Analysis
# --------------------------------------------------

st.divider()
st.subheader("SKU-Level Inventory Risk Analysis")

st.write(
    "Inspect inventory availability, reorder thresholds, "
    "supplier constraints, and purchase recommendations."
)

risk_store_options = sorted(
    recommendations["store_id"].unique().tolist()
)

risk_col1, risk_col2 = st.columns(2)

with risk_col1:
    risk_store = st.selectbox(
        "Inventory Risk - Store",
        risk_store_options,
        key="risk_store",
    )

risk_sku_options = sorted(
    recommendations.loc[
        recommendations["store_id"] == risk_store,
        "sku_id",
    ].unique().tolist()
)

with risk_col2:
    risk_sku = st.selectbox(
        "Inventory Risk - SKU",
        risk_sku_options,
        key="risk_sku",
    )

risk_row = recommendations[
    (recommendations["store_id"] == risk_store)
    & (recommendations["sku_id"] == risk_sku)
]

if not risk_row.empty:
    item = risk_row.iloc[0]

    st.markdown("#### Current Inventory Position")

    r1, r2, r3, r4 = st.columns(4)

    r1.metric(
        "On-Hand Units",
        f"{int(item['on_hand_units']):,}",
    )

    r2.metric(
        "On-Order Units",
        f"{int(item['on_order_units']):,}",
    )

    r3.metric(
        "Inventory Position",
        f"{int(item['inventory_position']):,}",
    )

    r4.metric(
        "Days of Cover",
        (
            f"{item['days_of_cover']:.1f}"
            if pd.notna(item["days_of_cover"])
            else "N/A"
        ),
    )

    st.markdown("#### Replenishment Policy")

    p1, p2, p3, p4 = st.columns(4)

    p1.metric(
        "Safety Stock",
        f"{int(item['safety_stock_units']):,}",
    )

    p2.metric(
        "Reorder Point",
        f"{int(item['reorder_point_units']):,}",
    )

    p3.metric(
        "Target Stock",
        f"{int(item['target_stock_units']):,}",
    )

    p4.metric(
        "Supplier Lead Time",
        f"{item['lead_time_mean_days']:.1f} days",
    )

    st.markdown("#### Purchase Recommendation")

    o1, o2, o3 = st.columns(3)

    o1.metric(
        "Recommended Quantity",
        f"{int(item['recommended_qty']):,} units",
    )

    o2.metric(
        "Estimated Purchase Cost",
        f"${item['estimated_order_cost']:,.2f}",
    )

    o3.metric(
        "Priority",
        item["priority"],
    )

    st.write(
        f"**Supplier:** {item['supplier_id']}  |  "
        f"**Pack Size:** {int(item['pack_size'])}  |  "
        f"**Minimum Order Quantity:** "
        f"{int(item['minimum_order_qty'])}"
    )

    if item["recommended_qty"] > 0:
        if item["priority"] == "Critical":
            st.error(
                "Critical inventory risk: the estimated "
                "inventory coverage is below the supplier "
                "lead time."
            )
        elif item["priority"] == "High":
            st.warning(
                "High inventory risk: estimated inventory "
                "coverage is below the replenishment "
                "protection period."
            )
        else:
            st.info(
                "A replenishment order is recommended."
            )
    else:
        st.success(
            "No additional purchase order is recommended "
            "under the current policy."
        )

    st.caption(
        "Risk classifications use inventory position "
        "(on-hand plus on-order) and do not yet account "
        "for the arrival dates of incoming stock."
    )
else:
    st.warning(
        "No inventory record found for this SKU-store pair."
    )


# --------------------------------------------------
# Store-Level Inventory Risk Summary
# --------------------------------------------------

st.divider()
st.subheader("Inventory Risk by Store")

store_risk = (
    recommendations.groupby("store_id")
    .agg(
        sku_count=("sku_id", "count"),
        recommended_orders=(
            "recommended_qty",
            lambda x: (x > 0).sum(),
        ),
        recommended_units=("recommended_qty", "sum"),
        estimated_cost=("estimated_order_cost", "sum"),
        critical_skus=(
            "priority",
            lambda x: (x == "Critical").sum(),
        ),
        high_risk_skus=(
            "priority",
            lambda x: (x == "High").sum(),
        ),
    )
    .reset_index()
)

st.dataframe(
    store_risk,
    hide_index=True,
    use_container_width=True,
)

st.subheader("Estimated Purchase Cost by Store")

cost_chart = store_risk.set_index("store_id")[
    "estimated_cost"
]

st.bar_chart(cost_chart)

st.caption(
    "Store-level totals reflect proposed replenishment "
    "quantities and estimated costs, not approved purchases."
)

# --------------------------------------------------
# Top 10 Purchase Recommendations
# --------------------------------------------------

st.divider()
st.subheader("Top 10 Purchase Recommendations")

top_orders = recommendations[
    recommendations["recommended_qty"] > 0
].copy()

top_orders = top_orders.sort_values(
    "estimated_order_cost",
    ascending=False,
).head(10)

display_columns = [
    "store_id",
    "sku_id",
    "supplier_id",
    "priority",
    "recommended_qty",
    "unit_cost",
    "estimated_order_cost",
]

st.dataframe(
    top_orders[display_columns],
    hide_index=True,
    use_container_width=True,
)

st.subheader("Highest-Cost Purchase Recommendations")

top_orders_chart = top_orders.copy()

top_orders_chart["SKU / Store"] = (
    top_orders_chart["sku_id"]
    + " / "
    + top_orders_chart["store_id"]
)

st.bar_chart(
    top_orders_chart.set_index("SKU / Store")[
        "estimated_order_cost"
    ]
)

st.caption(
    "These are the 10 highest-cost proposed purchase "
    "recommendations across all stores."
)
