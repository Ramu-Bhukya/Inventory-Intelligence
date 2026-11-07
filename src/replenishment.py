
import pandas as pd

from src.database import get_connection, load_config


def load_replenishment_inputs():
    con = get_connection()

    try:
        inventory = con.execute("""
            SELECT
                store_id,
                sku_id,
                snapshot_date,
                on_hand_units,
                on_order_units
            FROM InventorySnapshot
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM InventorySnapshot
            )
        """).df()

        suppliers = con.execute("""
            SELECT
                ss.sku_id,
                ss.supplier_sku_id,
                ss.supplier_id,
                ss.pack_size,
                ss.minimum_order_qty,
                ss.unit_cost,
                s.lead_time_mean_days,
                s.lead_time_std_days
            FROM SupplierSKU ss
            JOIN Supplier s
                ON ss.supplier_id = s.supplier_id
        """).df()

    finally:
        con.close()

    forecasts = pd.read_csv(
        "outputs/forecasts/baseline_forecast.csv"
    )

    return inventory, suppliers, forecasts


import math

import numpy as np
from scipy.stats import norm


def calculate_replenishment(
    inventory,
    suppliers,
    forecasts,
    service_level=0.95,
    review_period_days=7,
):
    if not 0 < service_level < 1:
        raise ValueError("service_level must be between 0 and 1")

    if review_period_days < 0:
        raise ValueError("review_period_days cannot be negative")

    daily_demand = (
        forecasts.groupby(["store_id", "sku_id"], as_index=False)
        ["predicted_demand"]
        .mean()
        .rename(columns={"predicted_demand": "daily_demand"})
    )

    planning = inventory.merge(
        daily_demand,
        on=["store_id", "sku_id"],
        how="left",
        validate="one_to_one",
    )

    planning = planning.merge(
        suppliers,
        on="sku_id",
        how="left",
        validate="many_to_one",
    )

    if planning[
        [
            "daily_demand",
            "pack_size",
            "minimum_order_qty",
            "lead_time_mean_days",
            "lead_time_std_days",
        ]
    ].isna().any().any():
        raise ValueError("Missing demand or supplier information")

    z = norm.ppf(service_level)

    recommendations = []

    for row in planning.itertuples(index=False):
        daily = max(0.0, float(row.daily_demand))
        lead_time = max(0.0, float(row.lead_time_mean_days))
        lead_std = max(0.0, float(row.lead_time_std_days))

        protection_days = lead_time + review_period_days

        # Approximate daily demand variance using a Poisson model.
        daily_variance = daily

        protection_variance = (
            protection_days * daily_variance
            + (daily ** 2) * (lead_std ** 2)
        )

        safety_stock = math.ceil(
            z * math.sqrt(max(0.0, protection_variance))
        )

        reorder_point = math.ceil(
            daily * lead_time + safety_stock
        )

        target_stock = math.ceil(
            daily * protection_days + safety_stock
        )

        inventory_position = (
            int(row.on_hand_units)
            + int(row.on_order_units)
        )
        pack_size = int(row.pack_size)
        minimum_order_qty = int(row.minimum_order_qty)

        # Only order when inventory position is at/below
        # the reorder point.
     
        # inventory_position = (
        #     int(row.on_hand_units)
        #     + int(row.on_order_units)
        # )

        # # Supplier constraints must be read for every row.
        # pack_size = int(row.pack_size)
        # minimum_order_qty = int(row.minimum_order_qty)
        inventory_position = (
            int(row.on_hand_units)
            + int(row.on_order_units)
        )

        # Supplier constraints must be read for every row.
        pack_size = int(row.pack_size)
        minimum_order_qty = int(row.minimum_order_qty)

        if pack_size <= 0 or minimum_order_qty <= 0:
            raise ValueError("Invalid supplier order constraints")

        # Only order when inventory reaches the reorder point.
        if inventory_position <= reorder_point:
            shortage = max(
                0,
                target_stock - inventory_position,
            )

            order_qty = max(
                shortage,
                minimum_order_qty,
            )

            order_qty = (
                math.ceil(order_qty / pack_size)
                * pack_size
            )
        else:
            order_qty = 0


     
        # Estimated purchase cost.
        unit_cost = float(row.unit_cost)
        estimated_order_cost = round(
            order_qty * unit_cost, 2
        )

        # Inventory coverage, based on inventory position.
        if daily > 0:
            days_of_cover = inventory_position / daily
        else:
            days_of_cover = float("inf")

        # Assign purchasing priority.
        if days_of_cover < lead_time:
            priority = "Critical"
        elif days_of_cover < protection_days:
            priority = "High"
        else:
            priority = "Normal"

        recommendations.append({
            "store_id": row.store_id,
            "sku_id": row.sku_id,
            "supplier_id": row.supplier_id,
            "daily_demand": round(daily, 2),
            "on_hand_units": int(row.on_hand_units),
            "on_order_units": int(row.on_order_units),
            "inventory_position": inventory_position,
            "lead_time_mean_days": round(lead_time, 2),
            "safety_stock_units": safety_stock,
            "reorder_point_units": reorder_point,
            "target_stock_units": target_stock,
            "pack_size": pack_size,
            "minimum_order_qty": minimum_order_qty,
            # "recommended_qty": order_qty,

            "recommended_qty": order_qty,
            "unit_cost": round(unit_cost, 2),
            "estimated_order_cost": estimated_order_cost,
            "days_of_cover": (
                round(days_of_cover, 2)
                if math.isfinite(days_of_cover)
                else None
            ),
            "priority": priority,


        })

    return pd.DataFrame(recommendations)


def main():
    config = load_config()

    inventory, suppliers, forecasts = (
        load_replenishment_inputs()
    )

    replenishment_config = config["replenishment"]

    recommendations = calculate_replenishment(
        inventory,
        suppliers,
        forecasts,
        service_level=replenishment_config["service_level"],
        review_period_days=replenishment_config[
            "review_period_days"
        ],
    )

    output_path = (
        "outputs/recommendations/replenishment.csv"
    )

    recommendations.to_csv(output_path, index=False)

    print(f"SKU-store combinations: {len(recommendations)}")

    orders = recommendations[
        recommendations["recommended_qty"] > 0
    ]

    print(f"Recommended purchase orders: {len(orders)}")
    print(
        "Total recommended units:",
        int(orders["recommended_qty"].sum()),
    )
    

    total_cost = orders["estimated_order_cost"].sum()

    print(f"Estimated purchase cost: ${total_cost:,.2f}")

    print("\nPurchase order priorities:")
    print(
        orders["priority"]
        .value_counts()
        .reindex(["Critical", "High", "Normal"], fill_value=0)
        .to_string()
    )

    print(f"Recommendations saved to: {output_path}")

    print("\nSample recommendations:")
    print(recommendations.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
