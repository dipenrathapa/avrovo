"use client";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "../lib/api";

type Patient = { id: string; name: string; age: number; conditions: string[] };

export default function Home() {
  const { data, error } = useSWR<Patient[]>("/patients", fetcher);
  return (
    <main style={{ maxWidth: 960, margin: "40px auto", padding: 16 }}>
      <h1 style={{ marginBottom: 4 }}>Avrovo</h1>
      <p style={{ color: "var(--muted)", marginTop: 0 }}>Family healthcare monitoring</p>
      {error && <p>Sign in required. <Link href="/login">Login</Link></p>}
      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fill, minmax(260px,1fr))" }}>
        {(data ?? []).map((p) => (
          <Link key={p.id} href={`/patient/${p.id}`} className="card" style={{ textDecoration: "none", color: "inherit" }}>
            <h3 style={{ margin: "0 0 6px" }}>{p.name}</h3>
            <div style={{ color: "var(--muted)" }}>Age {p.age}</div>
            <div style={{ marginTop: 8 }}>{(p.conditions ?? []).join(", ") || "no conditions"}</div>
          </Link>
        ))}
      </div>
    </main>
  );
}
