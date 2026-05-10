import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_signup_login_me(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "supersecret", "role": "family"})
    assert r.status_code == 201, r.text
    r2 = client.post("/auth/login", json={"email": "a@b.com", "password": "supersecret"})
    assert r2.status_code == 200
    tok = r2.json()["access_token"]
    r3 = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r3.status_code == 200
    assert r3.json()["role"] == "family"


def test_wrong_password(client):
    client.post("/auth/signup", json={"email": "x@y.com", "password": "supersecret"})
    r = client.post("/auth/login", json={"email": "x@y.com", "password": "wrong"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/signup", json={"email": "z@y.com", "password": "short"})
    assert r.status_code == 422
