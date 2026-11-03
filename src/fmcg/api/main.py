"""
FMCG SupplyChainIQ — FastAPI Application

Provides REST API endpoints for the FMCG monitoring system.
Reads actual data from MongoDB operational records and published
analytical results.

Long-running Spark jobs are NOT executed inside HTTP handlers.
Pipeline triggering uses a controlled mechanism that writes a run
request to MongoDB, which the pipeline runner picks up.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from fmcg.config.settings import EnvSettings
from fmcg.database.connection import close_mongo_client
from fmcg.services.data_service import (
    get_products, get_locations, get_inventory,
    get_expiry_items, get_shipments, get_forecasts,
    get_anomalies, get_pipeline_runs, get_dashboard_summary,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fmcg.api")

app = FastAPI(
    title="FMCG SupplyChainIQ API",
    description="Distributed FMCG Inventory Monitoring, Supply Chain Analytics and Demand Forecasting System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = EnvSettings()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
def shutdown():
    close_mongo_client()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health_check():
    """Check API and MongoDB health."""
    from fmcg.database.init_db import health_check as mongo_health
    mongo_status = mongo_health(settings)
    return {
        "status": "healthy" if mongo_status["status"] == "healthy" else "degraded",
        "database": mongo_status.get("database"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/summary", tags=["dashboard"])
async def summary():
    """Executive dashboard summary — aggregate metrics across all data."""
    try:
        return get_dashboard_summary(settings)
    except Exception as e:
        logger.error(f"Summary failed: {e}")
        raise HTTPException(status_code=503, detail=f"Data unavailable: {e}")


@app.get("/api/v1/products", tags=["products"])
async def products(
    category: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List products with optional category filter and search."""
    try:
        return get_products(settings, category=category, search=search,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Products query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/locations", tags=["locations"])
async def locations(
    location_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List locations with optional type filter."""
    try:
        return get_locations(settings, location_type=location_type,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Locations query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/inventory", tags=["inventory"])
async def inventory(
    sku_id: str | None = Query(None),
    location_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Current inventory levels (latest snapshot per SKU/location/batch)."""
    try:
        return get_inventory(settings, sku_id=sku_id, location_id=location_id,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Inventory query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/inventory/risks", tags=["inventory"])
async def inventory_risks(
    severity: str | None = Query(None),
):
    """Products with stockout risk."""
    try:
        return get_anomalies(settings, severity=severity)
    except Exception as e:
        logger.error(f"Inventory risks query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/batches/expiry", tags=["batches"])
async def batch_expiry(
    risk_level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Batch expiry analysis results."""
    try:
        return get_expiry_items(settings, risk_level=risk_level,
                               page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Expiry query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/shipments", tags=["shipments"])
async def shipments(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Shipment records with optional status filter."""
    try:
        return get_shipments(settings, status=status,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Shipments query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/demand/forecast", tags=["forecasting"])
async def demand_forecast(
    sku_id: str | None = Query(None),
    location_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    """Demand forecast predictions for the next 7 days."""
    try:
        return get_forecasts(settings, sku_id=sku_id, location_id=location_id,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Forecast query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/replenishment", tags=["inventory"])
async def replenishment(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Reorder recommendations for products at risk of stockout."""
    try:
        # Fetch stockout-risk alerts which include recommendations
        from fmcg.database.connection import get_database
        db = get_database(settings)
        coll = db["analytics_alerts"]
        query = {"alert_type": "stockout_risk", "acknowledged": False}
        total = coll.count_documents(query)
        skip = (page - 1) * page_size
        items = list(coll.find(query).skip(skip).limit(page_size))
        for item in items:
            item["_id"] = str(item["_id"])
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except Exception as e:
        logger.error(f"Replenishment query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/anomalies", tags=["anomalies"])
async def anomalies(
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Detected anomalies (demand spikes, inventory issues, shipment delays)."""
    try:
        return get_anomalies(settings, severity=severity,
                            page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Anomalies query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/pipeline/runs", tags=["pipeline"])
async def pipeline_runs(limit: int = Query(20, ge=1, le=100)):
    """Recent pipeline execution records."""
    try:
        return get_pipeline_runs(settings, limit=limit)
    except Exception as e:
        logger.error(f"Pipeline runs query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/v1/pipeline/run", tags=["pipeline"])
async def trigger_pipeline():
    """
    Trigger a pipeline run.

    This does NOT execute Spark jobs directly. It writes a run request
    to MongoDB that the pipeline runner process picks up asynchronously.

    This avoids long-running processes in HTTP handlers and prevents
    arbitrary shell execution through the API.
    """
    try:
        from fmcg.database.connection import get_database
        import uuid
        db = get_database(settings)
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        db["pipeline_runs"].insert_one({
            "run_id": run_id,
            "start_time": now,
            "end_time": None,
            "status": "queued",
            "records_ingested": 0,
            "records_processed": 0,
            "records_rejected": 0,
            "execution_duration": 0.0,
            "error_message": None,
        })

        return {
            "message": "Pipeline run queued",
            "run_id": run_id,
            "status": "queued",
            "note": "The pipeline runner will process this request asynchronously.",
        }
    except Exception as e:
        logger.error(f"Pipeline trigger failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Run the API with uvicorn."""
    import uvicorn
    uvicorn.run(
        "fmcg.api.main:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", "8000")),
        workers=int(os.environ.get("API_WORKERS", "2")),
        reload=False,
    )


if __name__ == "__main__":
    main()
