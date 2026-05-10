import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Avrovo — AI-powered family healthcare monitoring" },
      { name: "description", content: "Distributed FHIR-inspired healthcare simulation platform: FastAPI microservices, Kafka events, AI risk engine, real-time alerts." },
    ],
  }),
  component: Index,
});

function Service({ name, port, desc }: { name: string; port: string; desc: string }) {
  return (
    <div className="rounded-2xl border border-[hsl(35,30%,88%)] bg-white p-5 shadow-[0_1px_0_hsl(35,30%,90%)]">
      <div className="flex items-baseline justify-between">
        <h3 className="m-0 text-base font-semibold text-[hsl(20,25%,14%)]">{name}</h3>
        <span className="text-xs font-mono text-[hsl(20,15%,45%)]">:{port}</span>
      </div>
      <p className="mt-2 mb-0 text-sm text-[hsl(20,15%,38%)] leading-relaxed">{desc}</p>
    </div>
  );
}

function Index() {
  return (
    <main className="min-h-screen" style={{ backgroundColor: "#faf8f5", color: "#2a2520" }}>
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="mb-2 inline-block rounded-full bg-[hsl(95,20%,60%)]/15 px-3 py-1 text-xs font-medium text-[hsl(95,30%,30%)]">
          Distributed system · FastAPI · Kafka · Docker
        </div>
        <h1 className="mt-4 text-5xl font-semibold tracking-tight text-[hsl(20,25%,14%)]">Avrovo</h1>
        <p className="mt-3 max-w-2xl text-lg text-[hsl(20,15%,38%)] leading-relaxed">
          AI-powered family healthcare monitoring platform. FHIR-inspired data flows through six
          microservices, an event bus, and an AI engine that produces risk scores, trends, and
          natural-language summaries for family caregivers.
        </p>

        <div className="mt-6 rounded-2xl border border-[hsl(15,55%,52%)]/30 bg-[hsl(15,55%,52%)]/5 p-5 text-sm leading-relaxed text-[hsl(20,25%,20%)]">
          <strong>This preview is the landing page only.</strong> The actual distributed system lives
          under <code className="rounded bg-[hsl(35,30%,90%)] px-1.5 py-0.5 font-mono text-xs">services/</code> and{" "}
          <code className="rounded bg-[hsl(35,30%,90%)] px-1.5 py-0.5 font-mono text-xs">frontend/</code>. To run it,
          clone this repo locally and:
          <pre className="mt-3 overflow-x-auto rounded-lg bg-[hsl(20,25%,14%)] p-3 font-mono text-xs text-[hsl(35,30%,92%)]">
{`docker compose up --build`}
          </pre>
        </div>

        <h2 className="mt-12 mb-4 text-2xl font-semibold text-[hsl(20,25%,14%)]">Services</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Service name="api-gateway" port="8000" desc="FastAPI public entrypoint. JWT verify, RBAC, retries + circuit breaker, Prometheus metrics." />
          <Service name="patient-service" port="8001" desc="FHIR-like Patients, Observations, Encounters. Postgres + SQLAlchemy. Emits Kafka events." />
          <Service name="ai-engine" port="8002" desc="Consumes observation events. Risk score, trend slope detection, LLM summary with deterministic fallback." />
          <Service name="auth-service" port="8003" desc="JWT (HS256/RS256), Argon2id passwords, RBAC roles, audit log of sensitive actions." />
          <Service name="notification-service" port="8004" desc="Consumes alerts.raised. WebSocket fan-out to dashboard, mocked email." />
          <Service name="simulator" port="—" desc="Generates synthetic patients with disease progression and streaming vitals." />
        </div>

        <h2 className="mt-12 mb-4 text-2xl font-semibold text-[hsl(20,25%,14%)]">Architecture</h2>
        <ul className="space-y-2 text-sm text-[hsl(20,15%,30%)] leading-relaxed">
          <li><strong>Event-driven:</strong> Kafka topics <code className="font-mono text-xs">patient.events</code>, <code className="font-mono text-xs">observation.events</code>, <code className="font-mono text-xs">ai.insights</code>, <code className="font-mono text-xs">alerts.raised</code>. Append-only event log for replay.</li>
          <li><strong>FHIR-inspired models:</strong> shared Pydantic v2 schemas in <code className="font-mono text-xs">shared/fhir_models.py</code>.</li>
          <li><strong>Fault tolerance:</strong> tenacity retries with backoff, pybreaker circuit breakers, graceful AI degradation, idempotent consumers.</li>
          <li><strong>Observability:</strong> structlog JSON logs with request IDs, Prometheus <code className="font-mono text-xs">/metrics</code>, OTel traces, Grafana dashboards.</li>
          <li><strong>CI/CD:</strong> GitHub Actions — lint, type-check, tests with 80% coverage gate, Bandit + Trivy security scans, Docker builds, staging deploy.</li>
        </ul>

        <h2 className="mt-12 mb-4 text-2xl font-semibold text-[hsl(20,25%,14%)]">Getting started</h2>
        <ol className="space-y-2 text-sm text-[hsl(20,15%,30%)] leading-relaxed">
          <li>1. Read <code className="font-mono text-xs">README.md</code> and <code className="font-mono text-xs">ARCHITECTURE.md</code>.</li>
          <li>2. Copy <code className="font-mono text-xs">.env.example</code> → <code className="font-mono text-xs">.env</code>.</li>
          <li>3. Run <code className="font-mono text-xs">docker compose up --build</code>.</li>
          <li>4. Open <a className="underline" href="http://localhost:3000">localhost:3000</a> for the dashboard, <a className="underline" href="http://localhost:8000/docs">localhost:8000/docs</a> for the API.</li>
          <li>5. Run tests: <code className="font-mono text-xs">make test</code>.</li>
        </ol>

        <p className="mt-12 text-xs text-[hsl(20,15%,55%)]">
          Lovable hosts only this static landing page. The Python services and Next.js frontend run on your machine via Docker Compose.
        </p>
      </div>
    </main>
  );
}
