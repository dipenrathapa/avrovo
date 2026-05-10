from fastapi.testclient import TestClient
from app.main import app


def test_health():
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200


def test_metrics():
    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code == 200
