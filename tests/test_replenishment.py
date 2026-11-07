
import pandas as pd

from src.replenishment import (
    load_replenishment_inputs,
    calculate_replenishment,
)


def get_recommendations():
    inventory, suppliers, forecasts = (
        load_replenishment_inputs()
    )

    return calculate_replenishment(
        inventory,
        suppliers,
        forecasts,
        service_level=0.95,
        review_period_days=7,
    )


def test_recommendation_count():
    recommendations = get_recommendations()

    assert len(recommendations) == 250


def test_no_negative_order_quantities():
    recommendations = get_recommendations()

    assert (
        recommendations["recommended_qty"] >= 0
    ).all()


def test_pack_size_compliance():
    recommendations = get_recommendations()

    orders = recommendations[
        recommendations["recommended_qty"] > 0
    ]

    assert (
        orders["recommended_qty"]
        % orders["pack_size"] == 0
    ).all()


def test_minimum_order_quantity():
    recommendations = get_recommendations()

    orders = recommendations[
        recommendations["recommended_qty"] > 0
    ]

    assert (
        orders["recommended_qty"]
        >= orders["minimum_order_qty"]
    ).all()


def test_no_order_above_reorder_point():
    recommendations = get_recommendations()

    above = recommendations[
        recommendations["inventory_position"]
        > recommendations["reorder_point_units"]
    ]

    assert (above["recommended_qty"] == 0).all()


def test_safety_stock_nonnegative():
    recommendations = get_recommendations()

    assert (
        recommendations["safety_stock_units"] >= 0
    ).all()


def test_recommendation_file():
    recommendations = pd.read_csv(
        "outputs/recommendations/replenishment.csv"
    )

    assert len(recommendations) == 250
    assert recommendations["recommended_qty"].notna().all()



def test_supplier_constraints_preserved_when_no_order():
    import pandas as pd

    from src.replenishment import calculate_replenishment

    inventory = pd.DataFrame([
        {
            "store_id": "STORE_TEST",
            "sku_id": "SKU_A",
            "on_hand_units": 0,
            "on_order_units": 0,
        },
        {
            "store_id": "STORE_TEST",
            "sku_id": "SKU_B",
            "on_hand_units": 1000,
            "on_order_units": 0,
        },
    ])

    suppliers = pd.DataFrame([
        {
            "sku_id": "SKU_A",
            "supplier_sku_id": "SS_A",
            "supplier_id": "SUP_A",
            "pack_size": 6,
            "minimum_order_qty": 12,
            "unit_cost": 5.00,
            "lead_time_mean_days": 3.0,
            "lead_time_std_days": 1.0,
        },
        {
            "sku_id": "SKU_B",
            "supplier_sku_id": "SS_B",
            "supplier_id": "SUP_B",
            "pack_size": 48,
            "minimum_order_qty": 96,
            "unit_cost": 10.00,
            "lead_time_mean_days": 3.0,
            "lead_time_std_days": 1.0,
        },
    ])

    forecasts = pd.DataFrame([
        {
            "store_id": "STORE_TEST",
            "sku_id": "SKU_A",
            "predicted_demand": 10.0,
        },
        {
            "store_id": "STORE_TEST",
            "sku_id": "SKU_B",
            "predicted_demand": 10.0,
        },
    ])

    result = calculate_replenishment(
        inventory,
        suppliers,
        forecasts,
    ).set_index("sku_id")

    assert result.loc["SKU_A", "recommended_qty"] > 0
    assert result.loc["SKU_B", "recommended_qty"] == 0

    assert result.loc["SKU_A", "pack_size"] == 6
    assert result.loc["SKU_A", "minimum_order_qty"] == 12

    assert result.loc["SKU_B", "supplier_id"] == "SUP_B"
    assert result.loc["SKU_B", "pack_size"] == 48
    assert result.loc["SKU_B", "minimum_order_qty"] == 96
    assert result.loc["SKU_B", "unit_cost"] == 10.00

