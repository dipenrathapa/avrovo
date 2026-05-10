# Avrovo — System Architecture

## High-level diagram

```
                          ┌──────────────────────┐
                          │    Frontend (Next.js)│
                          │   /dashboard /patient│
                          └──────────┬───────────┘
                                     │ HTTPS
                                     ▼
                          ┌──────────────────────┐
                          │   API Gateway 8000   │  FastAPI
                          │  JWT verify, routing │
                          └──┬────────┬─────────┬┘
              ┌──────────────┘        │         └──────────────┐
              ▼                       ▼                        ▼
    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
    │ patient-service  │    │   auth-service   │    │ notification-svc │
    │   FastAPI 8001   │    │   FastAPI 8003   │    │   FastAPI 8004   │
    │   Postgres       │    │   Postgres       │    │   Redis pub/sub  │
    └────────┬─────────┘    └──────────────────┘    └────────▲─────────┘
             │ emits events                                  │ consumes alerts
             ▼                                               │
        ┌─────────────────────  Kafka  ─────────────────────┐│
        │  topics: patient.events, observation.events,      ││
        │          ai.insights, alerts                       ││
        └────────────┬───────────────────────────▲──────────┘│
                     │ consumes                  │ publishes  │
                     ▼                           │            │
            ┌──────────────────┐                 │            │
            │   ai-engine 8002 │─────────────────┘            │
            │   risk + trend   │                              │
            │   LLM summarizer │──────────── alerts ──────────┘
            └──────────────────┘

       ┌──────────────────┐
       │    simulator     │ generates synthetic patients,
       │   (worker)       │ vitals, labs → publishes to Kafka
       └──────────────────┘

   Observability: Prometheus scrapes /metrics on every service →
                  Grafana dashboards. Structured JSON logs with
                  correlation IDs propagated via X-Request-ID.
```

## Data model (FHIR-inspired)

Defined as Pydantic v2 models in `shared/fhir_models.py`:

- **Patient** — id, name, age, gender, conditions[]
- **MedicationRequest** — drug, dosage, frequency, start/end timestamps, status
- **Observation** — code (LOINC-like), value, unit, effective_at, patient_id
- **Encounter** — type (admission/discharge/visit), start, end, location

Validation: every API boundary uses these models. Inputs failing schema return `422`.

## Event-driven flow

1. `simulator` (or real ingest) writes a patient/observation → `patient-service`.
2. `patient-service` persists to Postgres, then publishes a typed event to Kafka:
   - `patient.created`, `observation.recorded`, `medication.prescribed`, `encounter.opened`.
3. `ai-engine` consumes `observation.recorded` events, computes risk score, trend, and an LLM summary, and republishes:
   - `ai.risk.computed`, `ai.summary.generated`, `alerts.raised` (LOW/MEDIUM/HIGH).
4. `notification-service` consumes `alerts.raised`, fans out to:
   - WebSocket → frontend toast
   - Email (mocked SMTP)
5. Every event is also written to an append-only `event_log` table for replay/audit.

## AI engine modules

- **Risk** — weighted score over latest vitals, abnormal labs, and high-risk meds. Deterministic, unit-tested.
- **Trend** — sliding window slope detection on observations of the same code; flags worsening trajectories.
- **Summarizer** — calls an LLM (configurable: OpenAI / local Ollama). Has a deterministic fallback template if the LLM call fails (graceful degradation).
- **Alerting** — combines risk + trend → severity bucket → emits `alerts.raised`.

## Auth & security

- JWT access tokens (RS256), refresh tokens stored hashed.
- Password hashing: argon2id.
- RBAC roles: `patient`, `family`, `admin`. Enforced via FastAPI dependency.
- Audit log table records every privileged action with actor, target, timestamp, IP.
- Pydantic validates every input; SQL via SQLAlchemy parameterized queries.
- Rate limiting at the gateway (slowapi).
- CORS locked to the frontend origin.

## Fault tolerance

- `tenacity` retries with exponential backoff on inter-service calls.
- `pybreaker` circuit breaker around AI engine and external LLM.
- AI engine has a deterministic fallback summarizer if the LLM breaker is open.
- Kafka consumer groups give at-least-once delivery; handlers are idempotent on `event_id`.
- Each service has `/healthz` (liveness) and `/readyz` (readiness) endpoints.
- `docker-compose.yml` sets `restart: unless-stopped` and healthchecks.

## Observability

- **Logs** — `structlog` JSON logs to stdout, with `request_id`, `service`, `user_id`, `event_id`.
- **Metrics** — `prometheus-client` exposes `/metrics`. Counters for events/sec, histograms for latency.
- **Tracing** — OpenTelemetry SDK, OTLP exporter, `traceparent` header propagated through gateway → services → Kafka headers.
- **Correlation** — middleware injects `X-Request-ID` if missing, propagates through Kafka headers.

## Environments

`.env.example` ships with safe defaults. `docker-compose.yml` is dev. `docker-compose.staging.yml` (override) uses managed Postgres / Kafka URLs and stricter CORS.
