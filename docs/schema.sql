
-- YottaFlex Inventory Forecasting POC
-- Relational Database Schema

-- 1. SKU Master
CREATE TABLE IF NOT EXISTS SKU (
    sku_id VARCHAR PRIMARY KEY,
    sku_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    launch_date DATE NOT NULL,
    status VARCHAR NOT NULL
        CHECK (status IN ('ACTIVE', 'DISCONTINUED'))
);

-- 2. Store Master
CREATE TABLE IF NOT EXISTS Store (
    store_id VARCHAR PRIMARY KEY,
    store_name VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    capacity_units INTEGER NOT NULL
        CHECK (capacity_units >= 0),
    status VARCHAR NOT NULL
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

-- 3. Supplier Master
CREATE TABLE IF NOT EXISTS Supplier (
    supplier_id VARCHAR PRIMARY KEY,
    supplier_name VARCHAR NOT NULL,
    lead_time_mean_days DOUBLE NOT NULL
        CHECK (lead_time_mean_days > 0),
    lead_time_std_days DOUBLE NOT NULL
        CHECK (lead_time_std_days >= 0),
    status VARCHAR NOT NULL
);

-- 4. Supplier-SKU Relationship
CREATE TABLE IF NOT EXISTS SupplierSKU (
    supplier_sku_id VARCHAR PRIMARY KEY,
    supplier_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    pack_size INTEGER NOT NULL
        CHECK (pack_size > 0),
    minimum_order_qty INTEGER NOT NULL
        CHECK (minimum_order_qty > 0),
    unit_cost DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (supplier_id)
        REFERENCES Supplier(supplier_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id),
    UNIQUE (supplier_id, sku_id)
);

-- 5. Sales History
CREATE TABLE IF NOT EXISTS SalesHistory (
    sale_id VARCHAR PRIMARY KEY,
    store_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    sale_date DATE NOT NULL,
    units_sold INTEGER NOT NULL
        CHECK (units_sold >= 0),
    promotion_flag BOOLEAN NOT NULL,
    stockout_flag BOOLEAN NOT NULL,
    FOREIGN KEY (store_id)
        REFERENCES Store(store_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id),
    UNIQUE (store_id, sku_id, sale_date)
);

-- 6. Inventory Snapshot
CREATE TABLE IF NOT EXISTS InventorySnapshot (
    snapshot_id VARCHAR PRIMARY KEY,
    store_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    snapshot_date DATE NOT NULL,
    on_hand_units INTEGER NOT NULL,
    on_order_units INTEGER NOT NULL,
    FOREIGN KEY (store_id)
        REFERENCES Store(store_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id),
    UNIQUE (store_id, sku_id, snapshot_date)
);

-- 7. Supplier Lead-Time Observations
CREATE TABLE IF NOT EXISTS LeadTimeObservation (
    observation_id VARCHAR PRIMARY KEY,
    supplier_sku_id VARCHAR NOT NULL,
    order_date DATE NOT NULL,
    receipt_date DATE NOT NULL,
    actual_lead_time_days INTEGER NOT NULL,
    FOREIGN KEY (supplier_sku_id)
        REFERENCES SupplierSKU(supplier_sku_id)
);

-- 8. Demand Forecast
CREATE TABLE IF NOT EXISTS Forecast (
    forecast_id VARCHAR PRIMARY KEY,
    store_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    forecast_date DATE NOT NULL,
    forecast_horizon_days INTEGER NOT NULL,
    predicted_demand DOUBLE NOT NULL,
    model_name VARCHAR NOT NULL,
    FOREIGN KEY (store_id)
        REFERENCES Store(store_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id)
);

-- 9. Reorder Policy
CREATE TABLE IF NOT EXISTS ReorderPolicy (
    policy_id VARCHAR PRIMARY KEY,
    store_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    service_level DOUBLE NOT NULL,
    safety_stock_units INTEGER NOT NULL,
    reorder_point_units INTEGER NOT NULL,
    FOREIGN KEY (store_id)
        REFERENCES Store(store_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id)
);

-- 10. Purchase Recommendation
CREATE TABLE IF NOT EXISTS PurchaseRecommendation (
    recommendation_id VARCHAR PRIMARY KEY,
    store_id VARCHAR NOT NULL,
    sku_id VARCHAR NOT NULL,
    forecast_id VARCHAR NOT NULL,
    policy_id VARCHAR NOT NULL,
    recommendation_date DATE NOT NULL,
    recommended_qty INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    reason VARCHAR,
    FOREIGN KEY (store_id)
        REFERENCES Store(store_id),
    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id),
    FOREIGN KEY (forecast_id)
        REFERENCES Forecast(forecast_id),
    FOREIGN KEY (policy_id)
        REFERENCES ReorderPolicy(policy_id)
);
