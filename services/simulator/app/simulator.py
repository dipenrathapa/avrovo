"""Synthetic patient + disease progression generator.

Posts to patient-service every few seconds. Vitals drift toward abnormal for
a fraction of patients to exercise the AI engine and alert pipeline.
"""
from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime
from uuid import uuid4

import httpx
import structlog

log = structlog.get_logger()
BASE = os.getenv("PATIENT_SERVICE_URL", "http://patient-service:8001")

NAMES = ["Ana Rivera", "Hiroshi Tanaka", "Olu Adebayo", "Maria Silva", "Liam O'Connor", "Priya Patel", "Ngozi Eze", "Chen Wei"]
CONDITIONS_POOL = [["hypertension"], ["diabetes"], ["copd"], ["heart_failure"], []]


async def seed(client: httpx.AsyncClient, n: int = 6) -> list[dict]:
    out = []
    for _ in range(n):
        body = {
            "id": str(uuid4()),
            "name": random.choice(NAMES),
            "age": random.randint(45, 88),
            "gender": random.choice(["male", "female"]),
            "conditions": random.choice(CONDITIONS_POOL),
        }
        try:
            r = await client.post(f"{BASE}/patients", json=body)
            r.raise_for_status()
            out.append(r.json())
        except Exception as e:
            log.warning("seed_failed", error=str(e))
    return out


def next_vital(state: dict, code: str) -> float:
    base = state.setdefault(code, {"heart_rate": 75, "spo2": 97, "systolic": 120, "glucose": 110, "temp_c": 36.8}.get(code, 50))
    drift = state.setdefault(f"{code}_drift", random.choice([-0.2, 0, 0, 0.2, 0.5]))
    base = base + drift + random.uniform(-1, 1)
    state[code] = base
    return round(base, 1)


async def loop():
    async with httpx.AsyncClient(timeout=10) as client:
        # wait for patient-service
        for _ in range(30):
            try:
                if (await client.get(f"{BASE}/healthz")).status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(2)
        patients = await seed(client)
        log.info("simulator_started", patients=len(patients))
        states: dict[str, dict] = {p["id"]: {} for p in patients}
        while True:
            for p in patients:
                for code, unit in [("heart_rate", "bpm"), ("spo2", "%"), ("systolic", "mmHg"), ("glucose", "mg/dL")]:
                    obs = {
                        "id": str(uuid4()),
                        "patient_id": p["id"],
                        "code": code,
                        "value": next_vital(states[p["id"]], code),
                        "unit": unit,
                        "effective_at": datetime.utcnow().isoformat(),
                    }
                    try:
                        await client.post(f"{BASE}/patients/{p['id']}/observations", json=obs)
                    except Exception as e:
                        log.warning("obs_post_failed", error=str(e))
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(loop())
