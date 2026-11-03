const fmcg = db.getSiblingDB("fmcg_supplychainiq");

const collections = [
    "products",
    "locations",
    "suppliers",
    "batches",
    "sales_transactions",
    "inventory_snapshots",
    "stock_movements",
    "shipments",
    "analytics_alerts",
    "forecasts",
    "pipeline_runs"
];

const existing = new Set(fmcg.getCollectionNames());

for (const name of collections) {
    if (!existing.has(name)) {
        fmcg.createCollection(name);
        print("Created collection: " + name);
    } else {
        print("Already exists: " + name);
    }
}

// Unique identifiers
fmcg.products.createIndex(
    { sku_id: 1 }, { unique: true }
);

fmcg.locations.createIndex(
    { location_id: 1 }, { unique: true }
);

fmcg.suppliers.createIndex(
    { supplier_id: 1 }, { unique: true }
);

fmcg.batches.createIndex(
    { batch_id: 1 }, { unique: true }
);

fmcg.sales_transactions.createIndex(
    { transaction_id: 1 }, { unique: true }
);

fmcg.inventory_snapshots.createIndex(
    { snapshot_id: 1 }, { unique: true }
);

fmcg.stock_movements.createIndex(
    { movement_id: 1 }, { unique: true }
);

fmcg.shipments.createIndex(
    { shipment_id: 1 }, { unique: true }
);

fmcg.analytics_alerts.createIndex(
    { alert_id: 1 }, { unique: true }
);

fmcg.forecasts.createIndex(
    {
        sku_id: 1,
        location_id: 1,
        forecast_date: 1,
        model_version: 1
    },
    { unique: true }
);

fmcg.pipeline_runs.createIndex(
    { run_id: 1 }, { unique: true }
);

// Analytical query indexes
fmcg.sales_transactions.createIndex(
    { sku_id: 1, store_id: 1, transaction_timestamp: -1 }
);

fmcg.inventory_snapshots.createIndex(
    { location_id: 1, sku_id: 1, snapshot_timestamp: -1 }
);

fmcg.batches.createIndex(
    { sku_id: 1, expiry_date: 1 }
);

fmcg.shipments.createIndex(
    { shipment_status: 1, expected_delivery_timestamp: 1 }
);

fmcg.analytics_alerts.createIndex(
    { severity: 1, created_at: -1 }
);

print("\nFMCG SupplyChainIQ database initialized.");
print("Collections:");
printjson(fmcg.getCollectionNames());

print("\nMongoDB connectivity:");
printjson(fmcg.runCommand({ ping: 1 }));
