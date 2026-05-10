"""AI engine — consumes observation events from Kafka, computes risk + trend +
summary, publishes ai.insights and alerts.raised. Also exposes REST for ad-hoc
scoring and frontend on-demand calls.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel

from shared.fhir_models import AlertEvent, EventEnvelope, Severity
from .risk import compute_risk
from .summarizer import summarize
from .trend import detect_trend

log = structlog.get_logger()
KAFKA = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

INSIGHTS_OUT = Counter("ai_insights_total", "insights produced", ["severity"])
ALERTS_OUT = Counter("ai_alerts_total", "alerts raised", ["severity"])

# in-memory series cache; in prod this would be a DB read
_series: dict[str, dict[str, deque[tuple[datetime, float]]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=50)))
_latest: dict[str, dict[str, float]] = defaultdict(dict)


class ScoreRequest(BaseModel):
    patient: dict
    observations: list[dict]
    medications: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = None
    producer = None
    try:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA)
        await producer.start()
        consumer = AIOKafkaConsumer("observation.events", bootstrap_servers=KAFKA, group_id="ai-engine", auto_offset_reset="latest")
        await consumer.start()
        app.state.producer = producer
        consumer_task = asyncio.create_task(_consume(app, consumer))
    except Exception as e:
        log.warning("kafka_unavailable", error=str(e))
        app.state.producer = None
    yield
    if consumer_task:
        consumer_task.cancel()
    if producer:
        await producer.stop()


async def _consume(app: FastAPI, consumer: AIOKafkaConsumer) -> None:
    async for msg in consumer:
        try:
            env = EventEnvelope.model_validate_json(msg.value)
            if env.event_type != "observation.recorded":
                continue
            obs = env.payload
            pid = obs["patient_id"]
            ts = datetime.fromisoformat(obs["effective_at"].replace("Z", ""))
            _series[pid][obs["code"]].append((ts, float(obs["value"])))
            _latest[pid][obs["code"]] = float(obs["value"])
            risk = compute_risk(_latest[pid], conditions=[], meds=[])
            risk.patient_id = pid  # type: ignore[assignment]
            trend = detect_trend(list(_series[pid][obs["code"]]))
            summary = await summarize({"id": pid}, risk.model_dump(), trend)
            insight = {
                "patient_id": pid,
                "risk": risk.model_dump(mode="json"),
                "trend": trend,
                "summary": summary,
            }
            INSIGHTS_OUT.labels(risk.severity.value).inc()
            await app.state.producer.send_and_wait(
                "ai.insights",
                EventEnvelope(event_type="ai.insight", payload=insight, correlation_id=env.correlation_id).model_dump_json().encode(),
            )
            if risk.severity in (Severity.medium, Severity.high):
                alert = AlertEvent(
                    patient_id=pid,
                    severity=risk.severity,
                    title=f"{risk.severity.value} risk detected",
                    body=summary,
                )
                ALERTS_OUT.labels(risk.severity.value).inc()
                await app.state.producer.send_and_wait(
                    "alerts.raised",
                    EventEnvelope(event_type="alert.raised", payload=alert.model_dump(mode="json"), correlation_id=env.correlation_id).model_dump_json().encode(),
                )
        except Exception:
            log.exception("ai_consume_failed")


app = FastAPI(title="Avrovo AI Engine", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/score")
async def score(req: ScoreRequest):
    latest = {o["code"]: float(o["value"]) for o in req.observations}
    risk = compute_risk(latest, req.patient.get("conditions", []), req.medications)
    points = [(datetime.fromisoformat(o["effective_at"].replace("Z", "")), float(o["value"])) for o in req.observations]
    trend = detect_trend(points)
    summary = await summarize(req.patient, risk.model_dump(), trend)
    return {"risk": risk.model_dump(mode="json"), "trend": trend, "summary": summary}
