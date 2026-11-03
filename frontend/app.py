#!/usr/bin/env python3
"""
FMCG SupplyChainIQ — Streamlit Dashboard

Professional FMCG supply chain monitoring dashboard.
Fetches real data from the FastAPI backend — never hardcodes metrics.

Pages:
1. Executive Dashboard
2. Inventory Intelligence
3. Batch & Expiry Monitoring
4. Demand Forecasting
5. Supply Chain Monitoring
6. Anomaly Monitoring
7. Pipeline Monitoring
"""

import os
import sys

import streamlit as st
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def api_get(endpoint: str, params: dict | None = None) -> dict | None:
    """Fetch data from the FastAPI backend."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API error ({resp.status_code}): {resp.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_BASE_URL}. Is the backend running?")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def render_empty_state(message: str):
    """Render a placeholder when no data is available."""
    st.info(f"📊 {message}")


def paginate(items: list, page_size: int, key_prefix: str):
    """Simple pagination widget."""
    if not items:
        return []
    total_pages = (len(items) + page_size - 1) // page_size
    page = st.number_input("Page", min_value=1, max_value=max(1, total_pages),
                          value=1, key=f"{key_prefix}_page")
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


# ---------------------------------------------------------------------------
# Page navigation
# ---------------------------------------------------------------------------

PAGES = {
    "Executive Dashboard": "pages/01_executive_dashboard.py",
    "Inventory Intelligence": "pages/02_inventory_intelligence.py",
    "Batch & Expiry Monitoring": "pages/03_batch_expiry.py",
    "Demand Forecasting": "pages/04_demand_forecasting.py",
    "Supply Chain Monitoring": "pages/05_supply_chain.py",
    "Anomaly Monitoring": "pages/06_anomaly_monitoring.py",
    "Pipeline Monitoring": "pages/07_pipeline_monitoring.py",
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="FMCG SupplyChainIQ",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("FMCG SupplyChainIQ")
    st.sidebar.caption("Distributed FMCG Inventory Monitoring & Analytics")

    # API health check
    health = api_get("/health")
    if health and health.get("status") == "healthy":
        st.sidebar.success("API: Connected")
    else:
        st.sidebar.warning("API: Unavailable")

    st.sidebar.divider()
    page = st.sidebar.selectbox("Navigation", list(PAGES.keys()))

    if page == "Executive Dashboard":
        render_executive_dashboard()
    elif page == "Inventory Intelligence":
        render_inventory_intelligence()
    elif page == "Batch & Expiry Monitoring":
        render_batch_expiry()
    elif page == "Demand Forecasting":
        render_demand_forecasting()
    elif page == "Supply Chain Monitoring":
        render_supply_chain()
    elif page == "Anomaly Monitoring":
        render_anomaly_monitoring()
    elif page == "Pipeline Monitoring":
        render_pipeline_monitoring()


# ---------------------------------------------------------------------------
# Page: Executive Dashboard
# ---------------------------------------------------------------------------

def render_executive_dashboard():
    st.title("📦 Executive Dashboard")
    st.markdown("Overview of FMCG supply chain health")

    data = api_get("/api/v1/summary")
    if not data:
        render_empty_state("No summary data available. Run the pipeline first.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total SKUs", data.get("total_skus", 0))
        st.metric("Stockout Risk", data.get("stockout_risk_products", 0))
    with col2:
        st.metric("Active Locations", data.get("total_locations", 0))
        st.metric("Expiry Risk Batches", data.get("expiry_risk_batches", 0))
    with col3:
        st.metric("Total Inventory (units)", f"{data.get('total_inventory_units', 0):,}")
        st.metric("Delayed Shipments", data.get("delayed_shipments", 0))

    if data.get("latest_pipeline_status"):
        st.divider()
        st.subheader("Latest Pipeline Run")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"Status: **{data['latest_pipeline_status']}**")
        with col_b:
            st.write(f"Run ID: `{data.get('latest_pipeline_run_id', 'N/A')}`")


# ---------------------------------------------------------------------------
# Page: Inventory Intelligence
# ---------------------------------------------------------------------------

def render_inventory_intelligence():
    st.title("📋 Inventory Intelligence")
    st.markdown("Product-level stock, days remaining, stockout alerts, and reorder recommendations")

    col1, col2 = st.columns(2)
    with col1:
        sku_filter = st.text_input("Filter by SKU ID", "")
    with col2:
        loc_filter = st.text_input("Filter by Location ID", "")

    params = {}
    if sku_filter:
        params["sku_id"] = sku_filter
    if loc_filter:
        params["location_id"] = loc_filter

    data = api_get("/api/v1/inventory", params=params)
    if not data or not data.get("items"):
        render_empty_state("No inventory data available.")
        return

    st.subheader(f"Inventory Items ({data.get('total', 0):,} total)")
    items = data["items"]

    df_data = []
    for item in items:
        df_data.append({
            "SKU": item.get("sku_id", ""),
            "Location": item.get("location_id", ""),
            "Batch": item.get("batch_id", ""),
            "On Hand": item.get("on_hand_quantity", 0),
            "Reserved": item.get("reserved_quantity", 0),
            "Available": item.get("available_stock", 0),
        })

    st.dataframe(df_data, use_container_width=True)

    # Replenishment recommendations
    st.divider()
    st.subheader("Reorder Recommendations")
    replen = api_get("/api/v1/replenishment")
    if replen and replen.get("items"):
        for item in replen["items"][:20]:
            st.warning(f"**{item.get('sku_id', 'N/A')}** at {item.get('location_id', 'N/A')}: "
                      f"{item.get('alert_description', '')} — {item.get('recommendation', '')}")
    else:
        render_empty_state("No reorder recommendations at this time.")


# ---------------------------------------------------------------------------
# Page: Batch & Expiry Monitoring
# ---------------------------------------------------------------------------

def render_batch_expiry():
    st.title("📅 Batch & Expiry Monitoring")
    st.markdown("Track batch expiry dates and FEFO dispatch recommendations")

    risk_filter = st.selectbox("Filter by Risk Level",
                                ["All", "expired", "critical", "approaching", "healthy"])
    params = {}
    if risk_filter != "All":
        params["risk_level"] = risk_filter

    data = api_get("/api/v1/batches/expiry", params=params)
    if not data or not data.get("items"):
        render_empty_state("No expiry data available. Run the expiry analytics pipeline.")
        return

    st.subheader(f"Batch Expiry Analysis ({data.get('total', 0):,} items)")
    items = data["items"]

    for item in items[:50]:
        risk = item.get("severity", "unknown")
        icon = {"expired": "🔴", "critical": "🟠", "approaching": "🟡", "healthy": "🟢"}.get(risk, "⚪")
        st.write(f"{icon} **{item.get('batch_id', 'N/A')}** — {item.get('alert_description', '')}")


# ---------------------------------------------------------------------------
# Page: Demand Forecasting
# ---------------------------------------------------------------------------

def render_demand_forecasting():
    st.title("📈 Demand Forecasting")
    st.markdown("7-day demand predictions using Spark MLlib")

    col1, col2 = st.columns(2)
    with col1:
        sku_filter = st.text_input("SKU ID", "")
    with col2:
        loc_filter = st.text_input("Location ID", "")

    params = {}
    if sku_filter:
        params["sku_id"] = sku_filter
    if loc_filter:
        params["location_id"] = loc_filter

    data = api_get("/api/v1/demand/forecast", params=params)
    if not data or not data.get("items"):
        render_empty_state("No forecasts available. Run the forecasting pipeline.")
        return

    st.subheader(f"7-Day Forecasts ({data.get('total', 0):,} predictions)")
    items = data["items"]

    # Group by SKU/location and display
    try:
        import pandas as pd
        df = pd.DataFrame(items)
        if "forecast_date" in df.columns and "predicted_units" in df.columns:
            st.dataframe(df[["forecast_date", "sku_id", "location_id", "predicted_units"]],
                        use_container_width=True)

            # Simple chart
            if len(df) > 0:
                st.subheader("Forecast Trend")
                chart_df = df.groupby("forecast_date")["predicted_units"].sum().reset_index()
                st.line_chart(chart_df.set_index("forecast_date")["predicted_units"])
    except ImportError:
        st.dataframe(items)
    except Exception as e:
        st.error(f"Chart rendering failed: {e}")
        st.dataframe(items)


# ---------------------------------------------------------------------------
# Page: Supply Chain Monitoring
# ---------------------------------------------------------------------------

def render_supply_chain():
    st.title("🚚 Supply Chain Monitoring")
    st.markdown("Shipment records, delivery status, and supplier performance")

    status_filter = st.selectbox("Filter by Status",
                                  ["All", "pending", "in_transit", "delivered", "delayed", "cancelled"])
    params = {}
    if status_filter != "All":
        params["status"] = status_filter

    data = api_get("/api/v1/shipments", params=params)
    if not data or not data.get("items"):
        render_empty_state("No shipment data available.")
        return

    st.subheader(f"Shipments ({data.get('total', 0):,} total)")
    items = data["items"]

    # Status breakdown
    status_counts: dict[str, int] = {}
    for s in items:
        st_val = s.get("shipment_status", "unknown")
        status_counts[st_val] = status_counts.get(st_val, 0) + 1

    cols = st.columns(len(status_counts))
    for i, (status, count) in enumerate(status_counts.items()):
        with cols[i]:
            st.metric(status.replace("_", " ").title(), count)

    st.divider()
    st.dataframe(items[:100], use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Anomaly Monitoring
# ---------------------------------------------------------------------------

def render_anomaly_monitoring():
    st.title("⚠️ Anomaly Monitoring")
    st.markdown("Detected anomalies with supporting evidence")

    severity_filter = st.selectbox("Filter by Severity",
                                    ["All", "low", "medium", "high", "critical"])
    params = {}
    if severity_filter != "All":
        params["severity"] = severity_filter

    data = api_get("/api/v1/anomalies", params=params)
    if not data or not data.get("items"):
        render_empty_state("No anomalies detected. Run the anomaly detection pipeline.")
        return

    st.subheader(f"Anomalies ({data.get('total', 0):,} total)")
    items = data["items"]

    for item in items[:50]:
        sev = item.get("severity", "unknown")
        color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
        with st.expander(f"{color} [{sev.upper()}] {item.get('alert_type', 'N/A')} — {item.get('sku_id', '')}"):
            st.write(f"**Description:** {item.get('alert_description', 'N/A')}")
            st.write(f"**Recommendation:** {item.get('recommendation', 'N/A')}")
            st.write(f"**Location:** {item.get('location_id', 'N/A')}")
            st.write(f"**Created:** {item.get('created_at', 'N/A')}")


# ---------------------------------------------------------------------------
# Page: Pipeline Monitoring
# ---------------------------------------------------------------------------

def render_pipeline_monitoring():
    st.title("⚙️ Pipeline Monitoring")
    st.markdown("Track data pipeline execution status and data quality")

    data = api_get("/api/v1/pipeline/runs")
    if not data or not data.get("items"):
        render_empty_state("No pipeline runs recorded.")
        return

    items = data["items"]

    # Latest run details
    latest = items[0] if items else {}
    st.subheader("Latest Pipeline Run")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Run ID", latest.get("run_id", "N/A"))
        st.metric("Status", latest.get("status", "N/A"))
    with col2:
        st.metric("Records Ingested", latest.get("records_ingested", 0))
        st.metric("Records Processed", latest.get("records_processed", 0))
    with col3:
        st.metric("Records Rejected", latest.get("records_rejected", 0))
        st.metric("Duration (s)", f"{latest.get('execution_duration', 0):.1f}")

    if latest.get("error_message"):
        st.error(f"Error: {latest['error_message']}")

    st.divider()
    st.subheader("Recent Runs")
    st.dataframe(items, use_container_width=True)

    # Trigger new run
    st.divider()
    st.subheader("Trigger Pipeline Run")
    if st.button("Queue Pipeline Run", type="primary"):
        try:
            resp = requests.post(f"{API_BASE_URL}/api/v1/pipeline/run", timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                st.success(f"Pipeline queued: {result.get('run_id', 'N/A')}")
            else:
                st.error(f"Failed to queue: {resp.status_code}")
        except Exception as e:
            st.error(f"Request failed: {e}")


if __name__ == "__main__":
    main()
