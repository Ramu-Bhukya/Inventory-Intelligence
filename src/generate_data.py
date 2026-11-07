
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.database import get_connection, load_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_master_data():
    config = load_config()

    seed = config["project"]["seed"]
    sku_count = config["data_generation"]["sku_count"]
    store_count = config["data_generation"]["store_count"]
    supplier_count = config["data_generation"]["supplier_count"]

    rng = np.random.default_rng(seed)

    categories = [
        "Electronics",
        "Home",
        "Grocery",
        "Beauty",
        "Apparel",
    ]

    regions = [
        "North",
        "South",
        "East",
        "West",
        "Central",
    ]

    skus = []

    for i in range(1, sku_count + 1):
        category = categories[(i - 1) % len(categories)]

        skus.append({
            "sku_id": f"SKU{i:05d}",
            "sku_name": f"{category} Product {i}",
            "category": category,
            "unit_price": round(float(rng.uniform(5, 250)), 2),
            "launch_date": date(2025, 1, 1)
                + timedelta(days=int(rng.integers(0, 365))),
            "status": "ACTIVE",
        })

    stores = []

    for i in range(1, store_count + 1):
        stores.append({
            "store_id": f"STORE{i:03d}",
            "store_name": f"YottaFlex Store {i}",
            "region": regions[(i - 1) % len(regions)],
            "capacity_units": int(rng.integers(1000, 5000)),
            "status": "ACTIVE",
        })

    suppliers = []

    for i in range(1, supplier_count + 1):
        suppliers.append({
            "supplier_id": f"SUP{i:03d}",
            "supplier_name": f"Supplier {i}",
            "lead_time_mean_days": round(
                float(rng.uniform(2, 14)), 2
            ),
            "lead_time_std_days": round(
                float(rng.uniform(0.5, 3)), 2
            ),
            "status": "ACTIVE",
        })

    return {
        "SKU": pd.DataFrame(skus),
        "Store": pd.DataFrame(stores),
        "Supplier": pd.DataFrame(suppliers),
    }


def generate_supplier_sku_data(master_data):
    config = load_config()

    rng = np.random.default_rng(
        config["project"]["seed"] + 1
    )

    skus = master_data["SKU"]
    suppliers = master_data["Supplier"]

    supplier_ids = suppliers["supplier_id"].tolist()

    relationships = []

    for i, sku in skus.iterrows():
        supplier_id = supplier_ids[i % len(supplier_ids)]

        pack_size = int(rng.choice([6, 12, 24, 48]))
        pack_count = int(rng.integers(1, 5))

        minimum_order_qty = pack_size * pack_count

        unit_cost = round(
            float(sku["unit_price"])
            * float(rng.uniform(0.45, 0.75)),
            2,
        )

        relationships.append({
            "supplier_sku_id": f"SSKU{i + 1:05d}",
            "supplier_id": supplier_id,
            "sku_id": sku["sku_id"],
            "pack_size": pack_size,
            "minimum_order_qty": minimum_order_qty,
            "unit_cost": unit_cost,
        })

    return pd.DataFrame(relationships)


def generate_daily_demand(master_data):
    config = load_config()

    rng = np.random.default_rng(
        config["project"]["seed"] + 2
    )

    start_date = pd.Timestamp(
        config["data_generation"]["start_date"]
    )

    days = config["data_generation"]["days"]

    skus = master_data["SKU"]
    stores = master_data["Store"]

    sales_records = []
    truth_records = []

    for _, sku in skus.iterrows():
        sku_id = sku["sku_id"]

        # Each SKU has a different underlying demand level.
        base_demand = float(rng.uniform(3, 25))

        for _, store in stores.iterrows():
            store_id = store["store_id"]
            store_factor = float(rng.uniform(0.7, 1.3))

            for day_index in range(days):
                current_date = start_date + pd.Timedelta(
                    days=day_index
                )

                # No demand before product launch.
                if current_date.date() < sku["launch_date"]:
                    continue

                # Weekend demand differs from weekday demand.
                weekend_factor = (
                    1.25 if current_date.weekday() >= 5 else 1.0
                )

                # Promotions increase demand.
                promotion_flag = bool(rng.random() < 0.08)
                promotion_factor = (
                    1.6 if promotion_flag else 1.0
                )

                # Smooth seasonal variation.
                seasonal_factor = (
                    1.0
                    + 0.15 * np.sin(
                        2 * np.pi * day_index / 30
                    )
                )

                expected_demand = max(
                    0.0,
                    base_demand
                    * store_factor
                    * weekend_factor
                    * promotion_factor
                    * seasonal_factor,
                )

                true_demand = int(
                    rng.poisson(expected_demand)
                )

                # Temporary placeholder:
                # Inventory constraints will be added next.
                units_sold = true_demand
                stockout_flag = False

                sale_id = (
                    f"SALE-{sku_id}-{store_id}-"
                    f"{current_date:%Y%m%d}"
                )

                sales_records.append({
                    "sale_id": sale_id,
                    "store_id": store_id,
                    "sku_id": sku_id,
                    "sale_date": current_date.date(),
                    "units_sold": units_sold,
                    "promotion_flag": promotion_flag,
                    "stockout_flag": stockout_flag,
                })

                truth_records.append({
                    "store_id": store_id,
                    "sku_id": sku_id,
                    "date": current_date.date(),
                    "true_demand": true_demand,
                    "observed_sales": units_sold,
                    "promotion_flag": promotion_flag,
                    "stockout_flag": stockout_flag,
                })

    return (
        pd.DataFrame(sales_records),
        pd.DataFrame(truth_records),
    )


def simulate_inventory(sales_history, master_data):
    config = load_config()
    rng = np.random.default_rng(config["project"]["seed"] + 3)

    supplier_sku = master_data["SupplierSKU"]
    suppliers = master_data["Supplier"]

    supplier_info = supplier_sku.merge(
        suppliers,
        on="supplier_id",
        how="left",
    ).set_index("sku_id")

    updated_sales = []
    inventory_records = []
    truth_updates = []

    grouped = sales_history.groupby(
        ["store_id", "sku_id"],
        sort=True,
    )

    for (store_id, sku_id), group in grouped:
        group = group.sort_values("sale_date")

        info = supplier_info.loc[sku_id]

        pack_size = int(info["pack_size"])
        moq = int(info["minimum_order_qty"])
        lead_time_mean = float(info["lead_time_mean_days"])
        lead_time_std = float(info["lead_time_std_days"])

        # Start with limited stock to produce realistic stockouts.
        on_hand = int(rng.integers(30, 100))

        # Incoming deliveries: (arrival_date, quantity)
        incoming = []

        for _, row in group.iterrows():
            current_date = pd.Timestamp(row["sale_date"])

            # Receive any orders arriving today.
            arriving = [
                order for order in incoming
                if order[0] <= current_date
            ]

            on_hand += sum(qty for _, qty in arriving)

            incoming = [
                order for order in incoming
                if order[0] > current_date
            ]

            true_demand = int(row["units_sold"])

            # Sales cannot exceed available stock.
            units_sold = min(true_demand, on_hand)
            stockout_flag = units_sold < true_demand

            on_hand -= units_sold

            # Place a new order when inventory is low.
            on_order = sum(qty for _, qty in incoming)

            if on_hand + on_order < 40:
                target_quantity = max(
                    moq,
                    120 - (on_hand + on_order),
                )

                order_qty = (
                    (target_quantity + pack_size - 1)
                    // pack_size
                ) * pack_size

                lead_time = max(
                    1,
                    int(round(rng.normal(
                        lead_time_mean,
                        lead_time_std,
                    ))),
                )

                arrival_date = (
                    current_date
                    + pd.Timedelta(days=lead_time)
                )

                incoming.append(
                    (arrival_date, order_qty)
                )

            on_order = sum(qty for _, qty in incoming)

            updated_sales.append({
                "sale_id": row["sale_id"],
                "store_id": store_id,
                "sku_id": sku_id,
                "sale_date": current_date.date(),
                "units_sold": units_sold,
                "promotion_flag": bool(row["promotion_flag"]),
                "stockout_flag": stockout_flag,
            })

            inventory_records.append({
                "snapshot_id": (
                    f"INV-{sku_id}-{store_id}-"
                    f"{current_date:%Y%m%d}"
                ),
                "store_id": store_id,
                "sku_id": sku_id,
                "snapshot_date": current_date.date(),
                "on_hand_units": on_hand,
                "on_order_units": on_order,
            })

            truth_updates.append({
                "store_id": store_id,
                "sku_id": sku_id,
                "date": current_date.date(),
                "true_demand": true_demand,
                "observed_sales": units_sold,
                "lost_sales": true_demand - units_sold,
                "stockout_flag": stockout_flag,
            })

    return (
        pd.DataFrame(updated_sales),
        pd.DataFrame(inventory_records),
        pd.DataFrame(truth_updates),
    )


def generate_lead_time_observations(master_data):
    config = load_config()

    rng = np.random.default_rng(
        config["project"]["seed"] + 4
    )

    start_date = pd.Timestamp(
        config["data_generation"]["start_date"]
    )

    days = int(config["data_generation"]["days"])

    supplier_sku = master_data["SupplierSKU"]
    suppliers = master_data["Supplier"]

    supplier_info = supplier_sku.merge(
        suppliers,
        on="supplier_id",
        how="left",
        validate="many_to_one",
    )

    observations = []

    for _, row in supplier_info.iterrows():
        # Approximately one supplier order every 14 days.
        for day_index in range(0, days, 14):
            order_date = start_date + pd.Timedelta(
                days=day_index
            )

            actual_lead_time = max(
                1,
                int(round(rng.normal(
                    float(row["lead_time_mean_days"]),
                    float(row["lead_time_std_days"]),
                ))),
            )

            receipt_date = order_date + pd.Timedelta(
                days=actual_lead_time
            )

            # Only include orders received during
            # the historical simulation period.
            if receipt_date >= start_date + pd.Timedelta(days=days):
                continue

            observation_id = (
                f"LT-{row['supplier_sku_id']}-"
                f"{order_date:%Y%m%d}"
            )

            observations.append({
                "observation_id": observation_id,
                "supplier_sku_id": row["supplier_sku_id"],
                "order_date": order_date.date(),
                "receipt_date": receipt_date.date(),
                "actual_lead_time_days": actual_lead_time,
            })

    return pd.DataFrame(observations)

def save_data(data):
    connection = get_connection()

    
    try:
        connection.begin()

        # Refresh generated daily records inside the transaction.
        # If an insertion fails, the deletions are rolled back too.
        connection.execute("DELETE FROM SalesHistory")
        connection.execute("DELETE FROM InventorySnapshot")

        for table_name, dataframe in data.items():

            connection.register("generated_data", dataframe)

            try:
                columns = ", ".join(
                    f'"{column}"' for column in dataframe.columns
                )

                

                connection.execute(
                f'INSERT INTO "{table_name}" '
                f'({columns}) SELECT {columns} '
                 'FROM generated_data '
                 'ON CONFLICT DO NOTHING'
                )

    
            finally:
                connection.unregister("generated_data")

            print(
                f"{table_name}: {len(dataframe)} records saved"
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()





def main():
    print("Generating YottaFlex master data...")

    data = generate_master_data()

    print("Generating supplier-SKU relationships...")
    data["SupplierSKU"] = generate_supplier_sku_data(data)

    print("Generating 90 days of daily demand...")
    sales_history, ground_truth = generate_daily_demand(data)

    print("Simulating inventory and stockouts...")
    updated_sales, inventory, truth_updates = simulate_inventory(
        sales_history,
        data,
    )

    data["SalesHistory"] = updated_sales
    data["InventorySnapshot"] = inventory

    print("Generating supplier lead-time observations...")

    data["LeadTimeObservation"] = (
    generate_lead_time_observations(data)
    )


    # # Replace previous sales and inventory rows so reruns
    # # reflect the latest simulation.
    # connection = get_connection()
    # try:
    #     connection.execute("DELETE FROM SalesHistory")
    #     connection.execute("DELETE FROM InventorySnapshot")
    # finally:
    #     connection.close()

    # save_data(data)

    # Save generated records in one database transaction.
    save_data(data)


    ground_truth = ground_truth.drop(
        columns=["observed_sales", "stockout_flag"]
    ).merge(
        truth_updates[
            [
                "store_id",
                "sku_id",
                "date",
                "observed_sales",
                "lost_sales",
                "stockout_flag",
            ]
        ],
        on=["store_id", "sku_id", "date"],
        how="left",
        validate="one_to_one",
    )

    ground_truth_path = (
        PROJECT_ROOT
        / "data"
        / "ground_truth"
        / "daily_demand.parquet"
    )

    ground_truth_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ground_truth.to_parquet(
        ground_truth_path,
        index=False,
    )

    print(f"SalesHistory: {len(updated_sales)} rows")
    print(f"InventorySnapshot: {len(inventory)} rows")
    print(f"Stockout days: {int(updated_sales['stockout_flag'].sum())}")
    print(f"Lost sales units: {int(ground_truth['lost_sales'].sum())}")

    print("Inventory simulation completed!")




if __name__ == "__main__":
    main()


