
def test_master_data_is_reproducible():
    """The same configured seed must produce identical master data."""
    from pandas.testing import assert_frame_equal
    from src.generate_data import generate_master_data

    first_run = generate_master_data()
    second_run = generate_master_data()

    expected_tables = {"SKU", "Store", "Supplier"}

    assert set(first_run.keys()) == expected_tables
    assert set(second_run.keys()) == expected_tables

    for table_name in expected_tables:
        assert_frame_equal(
            first_run[table_name],
            second_run[table_name],
            check_exact=True,
        )



def test_supplier_sku_data_is_reproducible():
    """Supplier-SKU relationships must be identical across runs."""
    from pandas.testing import assert_frame_equal
    from src.generate_data import (
        generate_master_data,
        generate_supplier_sku_data,
    )

    first_master = generate_master_data()
    second_master = generate_master_data()

    first_run = generate_supplier_sku_data(first_master)
    second_run = generate_supplier_sku_data(second_master)

    assert not first_run.empty
    assert_frame_equal(
        first_run,
        second_run,
        check_exact=True,
    )


def test_daily_demand_is_reproducible():
    """Daily demand and ground truth must match across runs."""
    from pandas.testing import assert_frame_equal
    from src.generate_data import (
        generate_master_data,
        generate_daily_demand,
    )

    first_master = generate_master_data()
    second_master = generate_master_data()

    first_sales, first_truth = generate_daily_demand(
        first_master
    )
    second_sales, second_truth = generate_daily_demand(
        second_master
    )

    assert not first_sales.empty
    assert not first_truth.empty

    assert_frame_equal(
        first_sales,
        second_sales,
        check_exact=True,
    )

    assert_frame_equal(
        first_truth,
        second_truth,
        check_exact=True,
    )

def test_inventory_simulation_is_reproducible():
    """Inventory, stockouts, and lost sales must match across runs."""
    from pandas.testing import assert_frame_equal
    from src.generate_data import (
        generate_master_data,
        generate_supplier_sku_data,
        generate_daily_demand,
        simulate_inventory,
    )

    # Prepare the same synthetic inputs independently.
    first_master = generate_master_data()
    first_master["SupplierSKU"] = generate_supplier_sku_data(
        first_master
    )
    first_sales, _ = generate_daily_demand(first_master)

    second_master = generate_master_data()
    second_master["SupplierSKU"] = generate_supplier_sku_data(
        second_master
    )
    second_sales, _ = generate_daily_demand(second_master)

    # Each simulation returns:
    # updated sales, inventory snapshots, and ground-truth updates.
    first_results = simulate_inventory(
        first_sales,
        first_master,
    )
    second_results = simulate_inventory(
        second_sales,
        second_master,
    )

    assert len(first_results) == 3
    assert len(second_results) == 3

    for first_frame, second_frame in zip(
        first_results,
        second_results,
    ):
        assert not first_frame.empty
        assert_frame_equal(
            first_frame,
            second_frame,
            check_exact=True,
        )

    # Check the business logic as well as reproducibility.
    updated_sales, inventory, truth_updates = first_results

    assert (inventory["on_hand_units"] >= 0).all()
    assert (inventory["on_order_units"] >= 0).all()
    assert (truth_updates["lost_sales"] >= 0).all()

    assert (
        truth_updates["true_demand"]
        == truth_updates["observed_sales"]
        + truth_updates["lost_sales"]
    ).all()

    assert (
        truth_updates["stockout_flag"]
        == (truth_updates["lost_sales"] > 0)
    ).all()

    assert len(updated_sales) == len(inventory)
    assert len(updated_sales) == len(truth_updates)



def test_lead_time_observations_are_reproducible():
    """Supplier lead-time observations must match across runs."""
    from pandas.testing import assert_frame_equal
    from src.generate_data import (
        generate_master_data,
        generate_supplier_sku_data,
        generate_lead_time_observations,
    )

    # First independent run.
    first_master = generate_master_data()
    first_master["SupplierSKU"] = generate_supplier_sku_data(
        first_master
    )

    first_run = generate_lead_time_observations(
        first_master
    )

    # Second independent run.
    second_master = generate_master_data()
    second_master["SupplierSKU"] = generate_supplier_sku_data(
        second_master
    )

    second_run = generate_lead_time_observations(
        second_master
    )

    assert not first_run.empty

    assert_frame_equal(
        first_run,
        second_run,
        check_exact=True,
    )
