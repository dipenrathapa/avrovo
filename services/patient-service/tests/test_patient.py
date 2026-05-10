import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root for `shared`
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_create_and_get_patient(client):
    r = client.post("/patients", json={
        "name": "Jane Doe", "age": 67, "gender": "female",
        "conditions": ["hypertension"],
    })
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r2 = client.get(f"/patients/{pid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Jane Doe"


def test_invalid_age_rejected(client):
    r = client.post("/patients", json={"name": "x", "age": 999, "gender": "male"})
    assert r.status_code == 422


def test_observation_lifecycle(client):
    pid = client.post("/patients", json={"name": "P", "age": 50, "gender": "male"}).json()["id"]
    o = client.post(f"/patients/{pid}/observations", json={
        "patient_id": pid, "code": "heart_rate", "value": 88, "unit": "bpm",
    })
    assert o.status_code == 201
    lst = client.get(f"/patients/{pid}/observations").json()
    assert len(lst) == 1 and lst[0]["code"] == "heart_rate"
