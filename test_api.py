from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_core_demo_flow():
    summary = client.get('/api/v1/fleet/summary')
    assert summary.status_code == 200
    assert summary.json()['data_mode'] == 'synthetic'
    asset = client.get('/api/v1/assets/A-104/health')
    assert asset.status_code == 200
    assert asset.json()['rul']['p10'] < asset.json()['rul']['p50'] < asset.json()['rul']['p90']
    plan = client.post('/api/v1/optimize/schedule', json={'crew_capacity': 3, 'spare_disruption': True})
    assert plan.status_code == 200
    assert plan.json()['optimized_availability'] >= plan.json()['baseline_availability']
    approved = client.post(f"/api/v1/plans/{plan.json()['plan_id']}/approve", json={'decision':'approved','note':'Approved after spare review','actor':'Test Planner'})
    assert approved.status_code == 200
    assert client.get('/healthz').json()['status'] == 'ok'
