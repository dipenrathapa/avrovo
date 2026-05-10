# AVROVO

AI-powered family healthcare monitoring platform — a distributed, event-driven, FHIR-inspired simulation system.

> The Lovable preview only renders the marketing landing page in `src/routes/index.tsx`.
> The actual distributed backend lives in `services/` and `frontend/` and is meant to be run locally with Docker Compose.

## Quickstart

```bash
docker compose up --build
```

Then open:

- Frontend dashboard: http://localhost:3000
- API Gateway:        http://localhost:8000/docs
- Patient Service:    http://localhost:8001/docs
- AI Engine:          http://localhost:8002/docs
- Auth Service:       http://localhost:8003/docs
- Notification Svc:   http://localhost:8004/docs
- Kafka UI:           http://localhost:8080
- Prometheus:         http://localhost:9090
- Grafana:            http://localhost:3001

## Services

| Service              | Stack             | Port | Purpose                                       |
| -------------------- | ----------------- | ---- | --------------------------------------------- |
| api-gateway          | FastAPI           | 8000 | Single public entrypoint, auth, routing       |
| patient-service      | FastAPI + Postgres| 8001 | FHIR-like patients, observations, encounters  |
| ai-engine            | FastAPI           | 8002 | Risk score, trend detection, LLM summaries    |
| auth-service         | FastAPI + Postgres| 8003 | JWT, RBAC (patient/family/admin), audit log   |
| notification-service | FastAPI + Redis   | 8004 | Real-time alerts via WebSocket + email        |
| simulator            | Python worker     | —    | Synthetic patients, disease progression       |
| frontend             | Next.js 14        | 3000 | Family dashboard, charts, AI insights         |

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system diagram, data flow, and design notes.

## Repo layout

```
avrovo/
├─ services/
│  ├─ api-gateway/
│  ├─ patient-service/
│  ├─ ai-engine/
│  ├─ auth-service/
│  ├─ notification-service/
│  └─ simulator/
├─ shared/                     # shared FHIR-like Pydantic models
├─ frontend/                   # Next.js dashboard
├─ infra/
│  ├─ prometheus/
│  └─ grafana/
├─ .github/workflows/ci.yml
├─ docker-compose.yml
└─ ARCHITECTURE.md
```

## Testing

```bash
# all services
make test

# one service
cd services/ai-engine && pytest -v
```

## CI/CD

`.github/workflows/ci.yml` runs on every push:

1. Lint (ruff, black, mypy)
2. Unit + integration tests with coverage gate (80%)
3. Security scan (bandit, pip-audit, trivy)
4. Docker build for each service
5. Deploy to staging on `main` (placeholder)

Failing builds block merges.
