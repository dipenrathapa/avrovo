"""Patient service — FHIR-like resources, persists to Postgres, emits events."""
from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

import structlog
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from sqlalchemy import JSON, Column, DateTime, Float, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from shared.fhir_models import EventEnvelope, Observation, Patient

log = structlog.get_logger()
DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./patients.db")
KAFKA = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

EVENTS_OUT = Counter("patient_events_out_total", "events emitted", ["event_type"])

engine = create_async_engine(DB_URL, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class PatientRow(Base):
    __tablename__ = "patients"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Float, nullable=False)
    gender = Column(String, nullable=False)
    conditions = Column(JSON, default=list)
    family_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ObservationRow(Base):
    __tablename__ = "observations"
    id = Column(String, primary_key=True)
    patient_id = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    effective_at = Column(DateTime, default=datetime.utcnow)


class EventLogRow(Base):
    __tablename__ = "event_log"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA)
        await producer.start()
        app.state.producer = producer
    except Exception as e:  # graceful: dev/test without kafka
        log.warning("kafka_unavailable", error=str(e))
        app.state.producer = None
    yield
    if app.state.producer:
        await app.state.producer.stop()
    await engine.dispose()


app = FastAPI(title="Avrovo Patient Service", lifespan=lifespan)


async def db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


async def emit(app: FastAPI, event_type: str, payload: dict, correlation_id: str | None = None) -> None:
    env = EventEnvelope(event_type=event_type, payload=payload, correlation_id=correlation_id)
    EVENTS_OUT.labels(event_type).inc()
    # persist to event_log
    async with SessionLocal() as s:
        s.add(EventLogRow(id=str(env.event_id), event_type=event_type, payload=payload, occurred_at=env.occurred_at))
        await s.commit()
    if app.state.producer:
        topic = event_type.split(".")[0] + ".events"
        await app.state.producer.send_and_wait(topic, env.model_dump_json().encode())


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    async with SessionLocal() as s:
        await s.execute(select(1))
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Patient routes -----------------------------------------------------------

@app.post("/patients", status_code=201)
async def create_patient(p: Patient, request: Request, s: AsyncSession = Depends(db)):
    s.add(PatientRow(
        id=str(p.id), name=p.name, age=p.age, gender=p.gender.value,
        conditions=p.conditions, family_id=str(p.family_id) if p.family_id else None,
        created_at=p.created_at,
    ))
    await s.commit()
    await emit(request.app, "patient.created", json.loads(p.model_dump_json()), request.headers.get("x-request-id"))
    return p


@app.get("/patients/{patient_id}")
async def get_patient(patient_id: str, s: AsyncSession = Depends(db)):
    row = await s.get(PatientRow, patient_id)
    if not row:
        raise HTTPException(404, "Not found")
    return {
        "id": row.id, "name": row.name, "age": row.age, "gender": row.gender,
        "conditions": row.conditions or [], "family_id": row.family_id,
        "created_at": row.created_at,
    }


@app.get("/patients")
async def list_patients(s: AsyncSession = Depends(db)):
    rows = (await s.execute(select(PatientRow))).scalars().all()
    return [
        {"id": r.id, "name": r.name, "age": r.age, "gender": r.gender, "conditions": r.conditions or []}
        for r in rows
    ]


@app.post("/patients/{patient_id}/observations", status_code=201)
async def add_observation(patient_id: str, obs: Observation, request: Request, s: AsyncSession = Depends(db)):
    if str(obs.patient_id) != patient_id:
        raise HTTPException(400, "patient_id mismatch")
    s.add(ObservationRow(
        id=str(obs.id), patient_id=patient_id, code=obs.code,
        value=obs.value, unit=obs.unit, effective_at=obs.effective_at,
    ))
    await s.commit()
    await emit(request.app, "observation.recorded", json.loads(obs.model_dump_json()), request.headers.get("x-request-id"))
    return obs


@app.get("/patients/{patient_id}/observations")
async def list_observations(patient_id: str, s: AsyncSession = Depends(db)):
    rows = (await s.execute(
        select(ObservationRow).where(ObservationRow.patient_id == patient_id).order_by(ObservationRow.effective_at)
    )).scalars().all()
    return [
        {"id": r.id, "code": r.code, "value": r.value, "unit": r.unit, "effective_at": r.effective_at}
        for r in rows
    ]
