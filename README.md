# AVROVO

> AI-powered family healthcare monitoring platform — distributed, event-driven, FHIR-inspired.

Avrovo helps families monitor the health of elderly or at-risk relatives in real time. A continuous simulator generates patient vitals (heart rate, SpO2, blood pressure, glucose) that drift toward abnormal values over time. An AI engine watches every reading, computes a clinical risk score, detects worsening trends, and fires plain-English alerts to the family dashboard via WebSocket — all within seconds of a vital being recorded.

Built as a production-grade microservices system with Kafka event streaming, JWT-secured APIs, Prometheus observability, and a FHIR-inspired data model.

---

## Quickstart

```bash
git clone https://github.com/your-username/avrovo
cd avrovo
cp .env.example .env        # edit JWT_SECRET and JWT_PUBLIC_KEY to match
docker compose up --build
```

Then open:

| Interface | URL |
|---|---|
| Family Dashboard | http://localhost:3000 |
| API Gateway (Swagger) | http://localhost:8000/docs |
| Patient Service | http://localhost:8001/docs |
| AI Engine | http://localhost:8002/docs |
| Auth Service | http://localhost:8003/docs |
| Notification Service | http://localhost:8004/docs |
| Kafka UI | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

---

## Services

| Service | Stack | Port | Purpose |
|---|---|---|---|
| api-gateway | FastAPI | 8000 | Single public entrypoint, JWT auth, rate limiting, routing |
| patient-service | FastAPI + Postgres | 8001 | FHIR-like patients, observations, encounters, event log |
| ai-engine | FastAPI + Kafka | 8002 | Risk scoring, trend detection, LLM summaries |
| auth-service | FastAPI + Postgres | 8003 | JWT (HS256/RS256), RBAC, argon2id hashing, audit log |
| notification-service | FastAPI + Redis | 8004 | Real-time alerts via WebSocket + mock email |
| simulator | Python worker | — | Synthetic patients + disease progression, publishes to Kafka |
| frontend | Next.js 14 | 3000 | Family dashboard, live vitals charts, AI insights, alerts |

---

## Architecture

```
                      ┌──────────────────────┐
                      │  Frontend (Next.js)  │
                      │  /dashboard /patient │
                      └──────────┬───────────┘
                                 │ HTTPS
                                 ▼
                      ┌──────────────────────┐
                      │   API Gateway 8000   │  JWT verify · rate limit · routing
                      └──┬────────┬─────────┬┘
          ┌──────────────┘        │         └──────────────┐
          ▼                       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ patient-service  │    │   auth-service   │    │ notification-svc │
│   FastAPI 8001   │    │   FastAPI 8003   │    │   FastAPI 8004   │
│   Postgres       │    │   Postgres       │    │   Redis pub/sub  │
└────────┬─────────┘    └──────────────────┘    └────────▲─────────┘
         │ emits events                                   │ consumes alerts
         ▼                                                │
    ┌─────────────────── Kafka ──────────────────────────┐│
    │  patient.events · observation.events               ││
    │  ai.insights · alerts.raised                       ││
    └────────────┬──────────────────────▲────────────────┘│
                 │ consumes             │ publishes        │
                 ▼                      │                  │
        ┌──────────────────┐            │                  │
        │   ai-engine 8002 │────────────┘                  │
        │  risk · trend    │                               │
        │  LLM summarizer  │────────── alerts ─────────────┘
        └──────────────────┘

   ┌──────────────┐
   │  simulator   │  generates synthetic patients + vitals → Kafka
   └──────────────┘

   Observability: Prometheus scrapes /metrics on every service → Grafana
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full data flow and design decisions.

---

## How the AI Works

The AI engine has three components:

**Risk Scoring** (`services/ai-engine/app/risk.py`) — deterministic weighted scoring over latest vitals against clinical reference ranges (SpO2, heart rate, blood pressure, glucose, temperature). Abnormal readings add weighted penalty points. Chronic conditions (heart failure, COPD, diabetes) and polypharmacy add additional risk. Score 0–100 maps to LOW / MEDIUM / HIGH severity.

**Trend Detection** (`services/ai-engine/app/trend.py`) — sliding window linear regression (numpy polyfit) over the last 6 observations of each vital code. Detects worsening trajectories before they become critical.

**LLM Summarizer** (`services/ai-engine/app/summarizer.py`) — calls OpenAI GPT-4o-mini (set `LLM_PROVIDER=openai` + `OPENAI_API_KEY`) to generate plain-English summaries for family members. Falls back to a deterministic template if the LLM is unavailable (circuit breaker + graceful degradation).

---

## Data Model (FHIR-inspired)

Pydantic v2 models in `shared/fhir_models.py`, validated at every API boundary:

- **Patient** — id, name, age, gender, conditions[]
- **Observation** — LOINC-like code, value, unit, effective_at, patient_id
- **MedicationRequest** — drug, dosage, frequency, start/end, status
- **Encounter** — type (admission/discharge/visit/emergency), start, end, location
- **RiskScore** — score 0–100, severity, contributing_factors
- **AlertEvent** — severity, title, body, raised_at
- **EventEnvelope** — Kafka message wrapper with event_id, correlation_id

---

## Security

- JWT access tokens (HS256 dev / RS256 prod), 15-minute TTL
- Argon2id password hashing
- RBAC roles: `patient`, `family`, `admin` — enforced at gateway
- Audit log table: every privileged action recorded with actor, IP, timestamp
- Rate limiting at gateway (slowapi, 120 req/min)
- CORS locked to frontend origin
- Parameterized SQL via SQLAlchemy (no injection surface)

---

## Observability

- **Logs** — structlog JSON to stdout, `request_id` + `service` + `event_id` on every line
- **Metrics** — prometheus-client `/metrics` on every service; counters for events/sec, histograms for latency
- **Tracing** — OpenTelemetry SDK, `traceparent` propagated through gateway → services → Kafka headers
- **Correlation** — `X-Request-ID` injected by gateway middleware, propagated everywhere

---

## Fault Tolerance

- `tenacity` retries with exponential backoff on inter-service HTTP calls
- `pybreaker` circuit breaker around AI engine and external LLM
- Deterministic fallback summarizer when LLM breaker is open
- Kafka at-least-once delivery; handlers idempotent on `event_id`
- `restart: unless-stopped` + Docker healthchecks on every service
- `/healthz` (liveness) and `/readyz` (readiness) on every service

---

## Repo Layout

```
avrovo/
├─ services/
│  ├─ api-gateway/
│  ├─ patient-service/
│  ├─ ai-engine/
│  ├─ auth-service/
│  ├─ notification-service/
│  └─ simulator/
├─ shared/                     # shared FHIR-inspired Pydantic v2 models
├─ frontend/                   # Next.js 14 family dashboard
├─ infra/
│  ├─ prometheus/
│  └─ grafana/
├─ .github/workflows/ci.yml
├─ docker-compose.yml
└─ ARCHITECTURE.md
```

---

## Testing

```bash
# all services
make test

# one service
cd services/ai-engine && pytest -v

# with coverage
cd services/ai-engine && pytest --cov=app --cov-report=term-missing
```

---

## CI/CD

`.github/workflows/ci.yml` runs on every push to `main`:

1. Lint — ruff, black, mypy across all services
2. Unit + integration tests with 80% coverage gate
3. Security scan — bandit, pip-audit, trivy (HIGH/CRITICAL fail the build)
4. Docker build for every service
5. Deploy to staging on `main` (wire to your registry here)

Failing builds block merges.

---

## Grade 1 To-Do List

Work through these one per day. Each item maps to the evaluation criteria.

### Week 1 — Core Fixes & Real AI
- [ ] **Day 1** — Connect real LLM: set `LLM_PROVIDER=openai`, add `OPENAI_API_KEY` to `.env`, verify summaries are AI-generated not template
- [ ] **Day 2** — Fix `Severity.medium` display bug in `summarizer.py` (change `{sev}` to `{sev.value}`)
- [ ] **Day 3** — Store AI insights in Postgres: add `insights` table to patient-service, persist risk score + summary + trend per patient per observation
- [ ] **Day 4** — Add frontend insight history: show last 10 risk scores as a timeline on the patient detail page
- [ ] **Day 5** — Add signup page to frontend (`frontend/app/signup/page.tsx`) so users don't need curl to register
- [ ] **Day 6** — Fix JWT to use RSA key pair (RS256) in dev: generate keys, mount as Docker secrets, update auth-service and gateway
- [ ] **Day 7** — Rest + review everything works end to end

### Week 2 — Observability & Logging
- [ ] **Day 8** — Add Loki to `docker-compose.yml` for centralized log aggregation
- [ ] **Day 9** — Configure Grafana to use both Prometheus and Loki as data sources (provisioned, not manual)
- [ ] **Day 10** — Build and provision Grafana dashboard JSON: patient risk over time, alerts per severity, request latency, events/sec
- [ ] **Day 11** — Add HIPAA-style log redaction: strip patient names and emails from structlog output, replace with patient_id only
- [ ] **Day 12** — Add log-level alerting: if ERROR rate exceeds threshold, fire a Kafka alert
- [ ] **Day 13** — Add OpenTelemetry tracing to Jaeger: add Jaeger container, verify traces show full request path
- [ ] **Day 14** — Rest + review dashboards look good

### Week 3 — Testing & Security
- [ ] **Day 15** — Add pre-commit hooks: `.pre-commit-config.yaml` with ruff, black, mypy — runs automatically before every commit
- [ ] **Day 16** — Expand Hypothesis property-based tests in `test_ai.py`: fuzz all vital codes, all severity boundaries
- [ ] **Day 17** — Add integration test: full pipeline test that creates a patient, posts critical vitals, and asserts a HIGH alert is produced
- [ ] **Day 18** — Add test coverage reporting to CI: publish HTML coverage report as GitHub Actions artifact
- [ ] **Day 19** — Add TLS: nginx reverse proxy container with self-signed cert in front of api-gateway
- [ ] **Day 20** — Add MFA groundwork: TOTP secret generation on signup, verify endpoint (use `pyotp`)
- [ ] **Day 21** — Rest + security review

### Week 4 — FHIR & Compliance
- [ ] **Day 22** — Add proper LOINC codes to all observations: map `heart_rate` → `8867-4`, `spo2` → `59408-5`, `glucose` → `2339-0`, `systolic` → `8480-6`
- [ ] **Day 23** — Add FHIR R4 schema validation: use `fhir.resources` Python library to validate Observation resources before persistence
- [ ] **Day 24** — Add Medplum connection: configure Medplum as external FHIR server, sync patients and observations to it
- [ ] **Day 25** — Add automated FHIR compliance check to CI: script that posts test resources and validates responses
- [ ] **Day 26** — Add audit log API endpoint: `GET /admin/audit` (admin only) returns paginated audit log — demonstrate HIPAA audit trail
- [ ] **Day 27** — Add `docker-compose.staging.yml` override: managed Postgres URL, stricter CORS, RS256 keys, no simulator
- [ ] **Day 28** — Final review: run full test suite, check all 10 criteria, write a one-page self-assessment

---

*Built by Nepad — Health Informatics, Deggendorf Institute of Technology*