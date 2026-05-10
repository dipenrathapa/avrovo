"use client";
import useSWR from "swr";
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { API, authHeader, fetcher } from "../../../lib/api";

type Obs = { id: string; code: string; value: number; unit: string; effective_at: string };

export default function PatientDetail({ params }: { params: { id: string } }) {
  const { data: patient } = useSWR(`/patients/${params.id}`, fetcher);
  const { data: obs } = useSWR<Obs[]>(`/patients/${params.id}/observations`, fetcher, { refreshInterval: 4000 });
  const [insight, setInsight] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    if (!obs?.length) return;
    fetch(`${API}/ai/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify({ patient: patient ?? {}, observations: obs, medications: [] }),
    }).then((r) => r.json()).then(setInsight).catch(() => {});
  }, [obs, patient]);

  useEffect(() => {
    const ws = new WebSocket(`${API.replace(/^http/, "ws")}/notifications/ws`);
    ws.onmessage = (e) => {
      try { const msg = JSON.parse(e.data); if (msg.type === "alert") setAlerts((a) => [msg.data, ...a].slice(0, 10)); } catch {}
    };
    return () => ws.close();
  }, []);

  const series = (code: string) =>
    (obs ?? []).filter((o) => o.code === code).map((o) => ({ t: new Date(o.effective_at).toLocaleTimeString(), v: o.value }));

  return (
    <main style={{ maxWidth: 1100, margin: "40px auto", padding: 16 }}>
      <h1>{patient?.name}</h1>
      <p style={{ color: "var(--muted)" }}>Age {patient?.age} · {(patient?.conditions ?? []).join(", ")}</p>

      {insight && (
        <div className="card" style={{ marginBottom: 16 }}>
          <span className={`badge ${insight.risk.severity}`}>{insight.risk.severity}</span>
          <h3 style={{ margin: "8px 0" }}>Risk score: {insight.risk.score}/100</h3>
          <p>{insight.summary}</p>
          <small>Trend: {insight.trend.trend}</small>
        </div>
      )}

      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "1fr 1fr" }}>
        {["heart_rate", "spo2", "systolic", "glucose"].map((c) => (
          <div key={c} className="card">
            <h4 style={{ margin: "0 0 8px" }}>{c}</h4>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={series(c)}>
                <XAxis dataKey="t" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="v" stroke="#c4654a" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      {alerts.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Recent alerts</h3>
          {alerts.map((a, i) => (
            <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--surface)" }}>
              <span className={`badge ${a.severity}`}>{a.severity}</span> {a.title} — {a.body}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
