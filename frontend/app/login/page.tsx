"use client";
import { useState } from "react";
import { login } from "../../lib/api";
import { useRouter } from "next/navigation";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  return (
    <main style={{ maxWidth: 380, margin: "80px auto", padding: 16 }}>
      <h1>Sign in</h1>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try { await login(email, pw); router.push("/"); }
          catch { setErr("Invalid credentials"); }
        }}
      >
        <input className="card" style={{ width: "100%", marginBottom: 10 }} placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="card" style={{ width: "100%", marginBottom: 10 }} placeholder="password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
        <button className="btn" type="submit">Sign in</button>
        {err && <p style={{ color: "var(--primary)" }}>{err}</p>}
      </form>
    </main>
  );
}
