"""API Gateway — single public entrypoint, JWT verification, routing.

Runs on :8000. Forwards to internal services via HTTP, with retries + circuit
breaker. Emits Prometheus metrics and structured logs with correlation IDs.
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import httpx
import pybreaker
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from jose import JWTError, jwt
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from slowapi import Limiter
from slowapi.util import get_remote_address
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

PATIENT_URL = os.getenv("PATIENT_SERVICE_URL", "http://patient-service:8001")
AI_URL = os.getenv("AI_ENGINE_URL", "http://ai-engine:8002")
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8003")
NOTIF_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
JWT_PUBLIC = os.getenv("JWT_PUBLIC_KEY", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")  # RS256 in prod with mounted key

REQ_COUNT = Counter("gateway_requests_total", "requests", ["route", "status"])
REQ_LAT = Histogram("gateway_request_seconds", "latency", ["route"])

breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Avrovo API Gateway", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def correlation_and_metrics(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
    with REQ_LAT.labels(request.url.path).time():
        try:
            resp = await call_next(request)
        except Exception:
            REQ_COUNT.labels(request.url.path, "500").inc()
            log.exception("unhandled")
            raise
    resp.headers["x-request-id"] = rid
    REQ_COUNT.labels(request.url.path, str(resp.status_code)).inc()
    return resp


def verify_jwt(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        return jwt.decode(auth.split(" ", 1)[1], JWT_PUBLIC, algorithms=[JWT_ALG])
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}")


def require_role(*roles: str):
    def dep(claims: dict = Depends(verify_jwt)) -> dict:
        if claims.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return claims
    return dep


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.2, max=2))
@breaker
async def proxy(client: httpx.AsyncClient, method: str, url: str, **kw) -> httpx.Response:
    r = await client.request(method, url, **kw)
    if r.status_code >= 500:
        r.raise_for_status()
    return r


async def _forward(request: Request, target: str, path: str) -> Response:
    url = f"{target}{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host"}}
    body = await request.body()
    try:
        r = await proxy(request.app.state.http, request.method, url, headers=headers, content=body, params=request.query_params)
    except pybreaker.CircuitBreakerError:
        return JSONResponse({"error": "upstream unavailable"}, status_code=503)
    return Response(r.content, status_code=r.status_code, headers={"content-type": r.headers.get("content-type", "application/json")})


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz(request: Request):
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Public auth routes (no JWT needed)
@app.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def auth_proxy(path: str, request: Request):
    # return await _forward(request, AUTH_URL, f"/{path}")
    return await _forward(request, AUTH_URL, f"/auth/{path}")





# Public auth routes (no JWT needed)
@app.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def auth_proxy(path: str, request: Request):
    return await _forward(request, AUTH_URL, f"/auth/{path}")


# Protected routes
@app.api_route("/patients", methods=["GET", "POST"])
async def patients_list_proxy(request: Request, _: dict = Depends(verify_jwt)):
    return await _forward(request, PATIENT_URL, "/patients")









# Protected routes
@app.api_route("/patients/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def patients_proxy(path: str, request: Request, _: dict = Depends(verify_jwt)):
    return await _forward(request, PATIENT_URL, f"/patients/{path}")


@app.api_route("/ai/{path:path}", methods=["GET", "POST"])
async def ai_proxy(path: str, request: Request, _: dict = Depends(verify_jwt)):
    return await _forward(request, AI_URL, f"/{path}")


@app.api_route("/notifications/{path:path}", methods=["GET", "POST"])
async def notif_proxy(path: str, request: Request, _: dict = Depends(verify_jwt)):
    return await _forward(request, NOTIF_URL, f"/{path}")
