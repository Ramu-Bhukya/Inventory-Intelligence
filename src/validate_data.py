
"""Validate generated YottaFlex data before forecasting."""

from pathlib import Path

import pandas as pd

from src.database import get_connection


GROUND_TRUTH_PATH = Path(
    "data/ground_truth/daily_demand.parquet"
)


def validate_data():
    """Run data quality checks and return a summary."""

    checks = {}

    con = get_connection()

    try:
        expected_counts = {
            "SKU": 50,
            "Store": 5,
            "Supplier": 10,
            "SupplierSKU": 50,
            "SalesHistory": 22500,
            "InventorySnapshot": 22500,
        }

        for table, expected in expected_counts.items():
            actual = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            checks[f"{table} row count"] = (
                actual == expected
            )

        negative_inventory = con.execute("""
            SELECT COUNT(*)
            FROM InventorySnapshot
            WHERE on_hand_units < 0
               OR on_order_units < 0
        """).fetchone()[0]

        checks["Nonnegative inventory"] = (
            negative_inventory == 0
        )

        invalid_lead_times = con.execute("""
            SELECT COUNT(*)
            FROM LeadTimeObservation
            WHERE actual_lead_time_days <= 0
               OR date_diff(
                   'day',
                   order_date,
                   receipt_date
               ) <> actual_lead_time_days
        """).fetchone()[0]

        checks["Valid supplier lead times"] = (
            invalid_lead_times == 0
        )

        missing_suppliers = con.execute("""
            SELECT COUNT(*)
            FROM SKU s
            LEFT JOIN SupplierSKU ss
                ON s.sku_id = ss.sku_id
            WHERE ss.sku_id IS NULL
        """).fetchone()[0]

        checks["Every SKU has a supplier"] = (
            missing_suppliers == 0
        )

        invalid_order_constraints = con.execute("""
            SELECT COUNT(*)
            FROM SupplierSKU
            WHERE pack_size <= 0
               OR minimum_order_qty <= 0
               OR minimum_order_qty % NULLIF(pack_size, 0) <> 0
        """).fetchone()[0]

        checks["Valid supplier order constraints"] = (
            invalid_order_constraints == 0
        )

    finally:
        con.close()

    if not GROUND_TRUTH_PATH.exists():
        checks["Ground truth exists"] = False
    else:
        ground_truth = pd.read_parquet(
            GROUND_TRUTH_PATH
        )

        checks["Ground truth row count"] = (
            len(ground_truth) == 22500
        )

        checks["Demand accounting"] = (
            (
                ground_truth["true_demand"]
                == (
                    ground_truth["observed_sales"]
                    + ground_truth["lost_sales"]
                )
            ).all()
        )

        checks["Nonnegative lost sales"] = (
            ground_truth["lost_sales"] >= 0
        ).all()

    return checks


def main():
    checks = validate_data()

    print("\nYottaFlex Data Validation")
    print("-" * 40)

    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")

    passed_count = sum(bool(value) for value in checks.values())

    print(
        f"\nResults: {passed_count}/{len(checks)} checks passed"
    )

    if passed_count != len(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
