
from src.database import get_connection


def test_database_connection():
    con = get_connection()

    try:
        result = con.execute("SELECT 1 + 1").fetchone()[0]
        assert result == 2
    finally:
        con.close()


def test_sku_count():
    con = get_connection()

    try:
        count = con.execute(
            "SELECT COUNT(*) FROM SKU"
        ).fetchone()[0]

        assert count == 50
    finally:
        con.close()


def test_sales_history_count():
    con = get_connection()
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM SalesHistory"
        ).fetchone()[0]
        assert count == 22500
    finally:
        con.close()


def test_inventory_snapshot_count():
    con = get_connection()
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM InventorySnapshot"
        ).fetchone()[0]
        assert count == 22500
    finally:
        con.close()


def test_no_negative_inventory():
    con = get_connection()
    try:
        count = con.execute("""
            SELECT COUNT(*)
            FROM InventorySnapshot
            WHERE on_hand_units < 0
               OR on_order_units < 0
        """).fetchone()[0]
        assert count == 0
    finally:
        con.close()


def test_supplier_lead_times():
    con = get_connection()
    try:
        count = con.execute("""
            SELECT COUNT(*)
            FROM LeadTimeObservation
            WHERE actual_lead_time_days <= 0
               OR date_diff(
                   'day',
                   order_date,
                   receipt_date
               ) <> actual_lead_time_days
        """).fetchone()[0]
        assert count == 0
    finally:
        con.close()


def test_ground_truth_consistency():
    import pandas as pd

    data = pd.read_parquet(
        "data/ground_truth/daily_demand.parquet"
    )

    assert len(data) == 22500

    assert (
        data["true_demand"]
        == data["observed_sales"] + data["lost_sales"]
    ).all()

    assert (data["lost_sales"] >= 0).all()


def test_supplier_sku_relationships():
    con = get_connection()
    try:
        missing = con.execute("""
            SELECT COUNT(*)
            FROM SKU s
            LEFT JOIN SupplierSKU ss
                ON s.sku_id = ss.sku_id
            WHERE ss.sku_id IS NULL
        """).fetchone()[0]

        assert missing == 0

        invalid_moq = con.execute("""
            SELECT COUNT(*)
            FROM SupplierSKU
            WHERE minimum_order_qty % pack_size <> 0
        """).fetchone()[0]

        assert invalid_moq == 0
    finally:
        con.close()
