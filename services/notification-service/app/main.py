"""Notification service — consumes alerts.raised, fans out via WebSocket + mock email."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager

import structlog
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

log = structlog.get_logger()
KAFKA = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
ALERTS = Counter("notif_alerts_total", "alerts received", ["severity"])

clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    try:
        consumer = AIOKafkaConsumer("alerts.raised", bootstrap_servers=KAFKA, group_id="notif", auto_offset_reset="latest")
        await consumer.start()
        task = asyncio.create_task(_consume(consumer))
    except Exception as e:
        log.warning("kafka_unavailable", error=str(e))
    yield
    if task:
        task.cancel()


async def _consume(consumer: AIOKafkaConsumer) -> None:
    async for msg in consumer:
        try:
            env = json.loads(msg.value)
            payload = env.get("payload", {})
            ALERTS.labels(payload.get("severity", "LOW")).inc()
            # mock email
            log.info("email_sent", to="family@example.com", subject=payload.get("title"))
            # fan out to websocket clients
            dead = []
            for ws in clients:
                try:
                    await ws.send_json({"type": "alert", "data": payload})
                except Exception:
                    dead.append(ws)
            for ws in dead:
                clients.discard(ws)
        except Exception:
            log.exception("notif_consume_failed")


app = FastAPI(title="Avrovo Notification Service", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/notifications/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
