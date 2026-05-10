export const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function login(email: string, password: string) {
  const r = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error("login failed");
  const data = await r.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

// export function authHeader() {
//   const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
//   return t ? { Authorization: `Bearer ${t}` } : {};
// }

export function authHeader(): Record<string, string> {
  const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}


export const fetcher = (url: string) =>
  fetch(`${API}${url}`, { headers: { ...authHeader() } }).then((r) => {
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  });
