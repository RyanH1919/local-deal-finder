const API_BASE = "http://localhost:8000";

export async function getDeals(filters = {}, { signal } = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.append(key, value);
  }
  const query = params.toString();
  const res = await fetch(`${API_BASE}/deals${query ? `?${query}` : ""}`, { signal });
  if (!res.ok) throw new Error(`GET /deals failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function dismissDeal(id) {
  const res = await fetch(`${API_BASE}/deals/${id}/dismiss`, { method: "POST" });
  if (!res.ok) throw new Error(`POST /deals/${id}/dismiss failed: ${res.status} ${res.statusText}`);
  return res.json();
}
