"""SIH26249: synthetic, explainable fleet maintenance decision prototype."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_ROOT = Path(__file__).parent
app = FastAPI(title="AeroNexus Fleet Intelligence", version="1.0.0")
app.mount("/static", StaticFiles(directory=APP_ROOT / "static"), name="static")


class ScenarioRequest(BaseModel):
    spare_disruption: bool = False
    crew_capacity: int = Field(default=3, ge=1, le=8)


class ApprovalRequest(BaseModel):
    decision: Literal["approved", "modified", "deferred", "rejected"]
    note: str = Field(min_length=3, max_length=280)
    actor: str = Field(default="Planner Asha", min_length=2, max_length=80)


NOW = datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc)
ASSETS = [
    {"id": "A-104", "platform": "Falcon X", "status": "at_risk", "availability": "Limited", "mission": "High", "component": "Hydraulic pump", "risk": 87, "rul": 42, "confidence": 0.86, "anomaly": 0.91, "criticality": 5, "sorties": 18, "health": 47},
    {"id": "A-117", "platform": "Falcon X", "status": "watch", "availability": "Available", "mission": "Medium", "component": "Avionics module", "risk": 62, "rul": 96, "confidence": 0.72, "anomaly": 0.78, "criticality": 4, "sorties": 11, "health": 65},
    {"id": "A-121", "platform": "Hawk M", "status": "healthy", "availability": "Available", "mission": "Medium", "component": "Engine temperature sensor", "risk": 18, "rul": 280, "confidence": 0.89, "anomaly": 0.14, "criticality": 3, "sorties": 22, "health": 91},
    {"id": "A-109", "platform": "Hawk M", "status": "watch", "availability": "Available", "mission": "High", "component": "Fuel control valve", "risk": 54, "rul": 118, "confidence": 0.76, "anomaly": 0.65, "criticality": 5, "sorties": 16, "health": 70},
    {"id": "A-132", "platform": "Falcon X", "status": "healthy", "availability": "Available", "mission": "Low", "component": "Landing gear actuator", "risk": 12, "rul": 360, "confidence": 0.92, "anomaly": 0.09, "criticality": 3, "sorties": 8, "health": 95},
    {"id": "A-145", "platform": "Hawk M", "status": "maintenance", "availability": "In maintenance", "mission": "Medium", "component": "Oil pump", "risk": 39, "rul": 162, "confidence": 0.81, "anomaly": 0.42, "criticality": 4, "sorties": 14, "health": 78},
]

AUDIT = [
    {"id": "evt-001", "time": "09:02", "actor": "Inference Engine", "event": "A-104 risk recalculated", "detail": "Risk 0.87; model rul-qrf-v1.2"},
    {"id": "evt-002", "time": "09:05", "actor": "Planner Asha", "event": "Scenario generated", "detail": "Base plan; 3 crew slots"},
]


def trend_for(asset: dict) -> list[dict]:
    points = []
    base = 47 if asset["id"] == "A-104" else 54
    slope = 1.3 if asset["risk"] > 70 else 0.55
    for i in range(30):
        residual = round(base + slope * i + ((i % 5) - 2) * 0.9, 1)
        points.append({"cycle": 301 + i, "pressure": residual, "vibration": round(2.3 + i * slope / 11 + (i % 4) * 0.08, 2)})
    return points


def plan_for(scenario: ScenarioRequest) -> dict:
    items = sorted(ASSETS, key=lambda a: a["risk"] * a["criticality"], reverse=True)
    actions = []
    day = NOW.replace(hour=10)
    used_slots = 0
    impacted = 0
    for index, asset in enumerate(items):
        if asset["risk"] < 45:
            action = "Monitor"
            state = "Deferred"
            hours = 0
        elif used_slots < scenario.crew_capacity:
            action = "Replace" if asset["risk"] > 75 else "Inspect"
            state = "Scheduled"
            hours = 3 if action == "Replace" else 1
            used_slots += 1
        else:
            action = "Inspect"
            state = "Queue"
            hours = 1
            impacted += 1

        blocked = scenario.spare_disruption and asset["id"] == "A-104"
        if blocked:
            state, action = "Spare constrained", "Inspect"
            hours = 1
            impacted += 1
        start = day + timedelta(hours=index * 2)
        actions.append({
            "task_id": f"MT-{104 + index}", "asset_id": asset["id"], "component": asset["component"],
            "action": action, "status": state, "risk": asset["risk"], "rul_hours": asset["rul"],
            "start": start.strftime("%a %H:%M"), "duration_hours": hours,
            "reason": f"{asset['risk']}% risk, {asset['rul']}h median RUL, {asset['mission'].lower()} mission priority",
            "spare": "Available" if not blocked else "Backorder 18h",
        })
    baseline = 66
    gain = 12 - impacted * 2 - (3 - min(scenario.crew_capacity, 3)) * 2
    optimized = max(baseline + max(gain, 2), baseline)
    return {
        "plan_id": "plan-" + ("spare" if scenario.spare_disruption else "base") + f"-c{scenario.crew_capacity}",
        "scenario": {"spare_disruption": scenario.spare_disruption, "crew_capacity": scenario.crew_capacity},
        "baseline_availability": baseline, "optimized_availability": optimized,
        "availability_gain": optimized - baseline, "expected_downtime_hours": 46 - (optimized - baseline) * 2,
        "objective_score": 71 + (optimized - baseline), "actions": actions,
        "assumptions": ["Synthetic data for demonstration only", "Safety-critical actions require human approval", "Planning horizon: next 48 hours"],
    }


@app.get("/", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(APP_ROOT / "static" / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "aeronexus-api", "data_mode": "synthetic"}


@app.get("/api/v1/fleet/summary")
def fleet_summary() -> dict:
    available = sum(a["availability"] == "Available" for a in ASSETS)
    return {
        "fleet_size": len(ASSETS), "available": available, "availability_percent": 67,
        "at_risk": sum(a["risk"] >= 50 for a in ASSETS), "maintenance": sum(a["availability"] == "In maintenance" for a in ASSETS),
        "data_freshness_seconds": 28, "model_version": "rul-qrf-v1.2", "data_mode": "synthetic",
        "availability_trend": [{"day": day, "baseline": value, "optimized": value + 7} for day, value in [("Mon", 64), ("Tue", 66), ("Wed", 63), ("Thu", 68), ("Fri", 70), ("Sat", 69), ("Sun", 67)]],
        "assets": ASSETS,
    }


@app.get("/api/v1/assets/{asset_id}/health")
def asset_health(asset_id: str) -> dict:
    asset = next((a for a in ASSETS if a["id"] == asset_id.upper()), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return {
        "asset": asset, "trend": trend_for(asset),
        "rul": {"p10": max(asset["rul"] - 24, 6), "p50": asset["rul"], "p90": asset["rul"] + 39, "confidence": asset["confidence"]},
        "evidence": [
            {"feature": "Pressure residual", "impact": "+23%", "direction": "increasing", "weight": 0.42},
            {"feature": "Vibration trend", "impact": "+18%", "direction": "increasing", "weight": 0.31},
            {"feature": "Temperature drift", "impact": "+9%", "direction": "increasing", "weight": 0.17},
            {"feature": "Recent cycles", "impact": "+6%", "direction": "increasing", "weight": 0.10},
        ],
        "model": {"version": "rul-qrf-v1.2", "trained_on": "synthetic-proxy-v3", "last_validated": "2026-10-03", "lineage": "telemetry-window-9ef21"},
    }


@app.post("/api/v1/optimize/schedule")
def optimize_schedule(scenario: ScenarioRequest) -> dict:
    plan = plan_for(scenario)
    AUDIT.insert(0, {"id": str(uuid4()), "time": datetime.now().strftime("%H:%M"), "actor": "Optimizer", "event": "Plan generated", "detail": f"{plan['plan_id']}; objective {plan['objective_score']}"})
    return plan


@app.post("/api/v1/plans/{plan_id}/approve")
def approve_plan(plan_id: str, approval: ApprovalRequest) -> dict:
    event = {"id": str(uuid4()), "time": datetime.now().strftime("%H:%M"), "actor": approval.actor, "event": f"Plan {approval.decision}", "detail": f"{plan_id}: {approval.note}"}
    AUDIT.insert(0, event)
    return {"plan_id": plan_id, "status": approval.decision, "audit_event": event}


@app.get("/api/v1/audit/events")
def audit_events() -> dict:
    return {"events": AUDIT[:20]}
