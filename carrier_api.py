from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional
import math

app = FastAPI(
    title="Carrier GPS Telemetry API",
    description="Logistics carrier tracking data API",
    version="1.0.0"
)

# Load CSV once at startup
print("Loading data...")
df = pd.read_csv("filesystem_carrier_gps_telemetry_fixed.csv")
df["is_active"] = df["is_active"].astype(bool)
print(f"Loaded {len(df)} records.")


# ─── ROUTE 1: Health Check ───────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Carrier GPS Telemetry API is running!", "total_records": len(df)}


# ─── ROUTE 2: Get All Records (paginated) ────────────────────────────────────
@app.get("/telemetry", tags=["Telemetry"])
def get_all_telemetry(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Records per page")
):
    total = len(df)
    total_pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    end = start + page_size

    data = df.iloc[start:end].to_dict(orient="records")

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total,
        "total_pages": total_pages,
        "data": data
    }


# ─── ROUTE 3: Get by Telemetry ID ────────────────────────────────────────────
@app.get("/telemetry/{telemetry_id}", tags=["Telemetry"])
def get_by_telemetry_id(telemetry_id: str):
    result = df[df["Telemetry_ID"] == telemetry_id]
    if result.empty:
        raise HTTPException(status_code=404, detail=f"Telemetry ID '{telemetry_id}' not found")
    return result.iloc[0].to_dict()


# ─── ROUTE 4: Get by Manifest ID ─────────────────────────────────────────────
@app.get("/telemetry/manifest/{manifest_id}", tags=["Telemetry"])
def get_by_manifest_id(manifest_id: str):
    result = df[df["Manifest_ID"] == manifest_id]
    if result.empty:
        raise HTTPException(status_code=404, detail=f"Manifest ID '{manifest_id}' not found")
    return result.to_dict(orient="records")


# ─── ROUTE 5: Get by Transit Node (Hub) ──────────────────────────────────────
@app.get("/telemetry/hub/{hub_name}", tags=["Telemetry"])
def get_by_hub(
    hub_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    result = df[df["Next_Transit_Node"].str.lower() == hub_name.lower()]
    if result.empty:
        raise HTTPException(status_code=404, detail=f"Hub '{hub_name}' not found")

    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "hub": hub_name,
        "total_records": total,
        "page": page,
        "data": result.iloc[start:end].to_dict(orient="records")
    }


# ─── ROUTE 6: High Delay Risk Shipments ──────────────────────────────────────
@app.get("/telemetry/alerts/high-delay", tags=["Alerts"])
def get_high_delay_risk(
    threshold: float = Query(80.0, description="Delay risk % threshold"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    result = df[df["Delay_Risk_Probability_Percentage"] >= threshold]
    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "threshold": threshold,
        "total_high_risk": total,
        "page": page,
        "data": result.iloc[start:end].to_dict(orient="records")
    }


# ─── ROUTE 7: Summary / Stats ─────────────────────────────────────────────────
@app.get("/telemetry/stats/summary", tags=["Stats"])
def get_summary():
    return {
        "total_records": len(df),
        "active_records": int(df["is_active"].sum()),
        "unique_hubs": df["Next_Transit_Node"].nunique(),
        "hub_list": df["Next_Transit_Node"].unique().tolist(),
        "avg_delay_risk": round(df["Delay_Risk_Probability_Percentage"].mean(), 2),
        "avg_temperature": round(df["Temperature_Log_Celsius"].mean(), 2),
        "high_delay_count": int((df["Delay_Risk_Probability_Percentage"] >= 80).sum()),
        "source_system": df["source_system"].iloc[0]
    }
