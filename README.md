# AeroNexus Fleet Intelligence

A complete SIH26249 prototype for predictive maintenance and fleet availability. It is an explicitly synthetic demonstration system: it models a fleet, exposes component health and remaining-useful-life intervals, explains risk drivers, converts risk into a constrained maintenance plan, compares availability before and after optimization, and records planner approval decisions.

## What works

- Fleet Command dashboard with readiness KPIs, risk queue, projected availability, and asset health map.
- Asset Health drill-down with a 30-cycle degradation trend, P10/P50/P90 RUL, confidence, data lineage, and feature-attribution evidence.
- Maintenance Planner with adjustable crew capacity and a critical-spare disruption what-if.
- Current-plan versus AI-plan availability comparison and realistic scheduling recommendations.
- Human approval workflow with decision note and audit log.
- API documented automatically at `/docs`.

The system uses deterministic synthetic/proxy data. It must not be presented as real operational aircraft data.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`.

## Deploy on Render

1. Push this folder to a GitHub repository.
2. In Render, select **New → Web Service → Build and deploy from a Git repository**.
3. Select the repository and choose **Docker** as the runtime. Render will use the included `Dockerfile` (or let Render import the included `render.yaml` Blueprint).
4. Leave the build/start commands blank. The container accepts Render's `PORT` environment variable automatically.
5. Choose a region, deploy, and open the generated `onrender.com` URL.

For Render health checks, use `/healthz`. No database or secrets are required for this self-contained prototype. In a production iteration, replace the in-memory synthetic store with PostgreSQL/TimescaleDB and protect planner actions with real authentication.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/fleet/summary` | Fleet KPIs, health map, availability trend |
| `GET /api/v1/assets/{id}/health` | Component trend, RUL interval, evidence |
| `POST /api/v1/optimize/schedule` | Generate a constrained maintenance plan |
| `POST /api/v1/plans/{id}/approve` | Record planner decision and note |
| `GET /api/v1/audit/events` | Read the decision trail |

## SIH demo flow

1. Start at Fleet Command and point out at-risk A-104.
2. Open its Asset Health view: pressure residual rises, risk is explained, and RUL is presented as a range instead of false precision.
3. Open Maintenance Planner. Generate the baseline AI plan.
4. Turn on **Critical spare disruption**, regenerate, and explain how the plan adapts.
5. Approve the plan and show the resulting audit event.

## Verification

```powershell
pytest -q
```
