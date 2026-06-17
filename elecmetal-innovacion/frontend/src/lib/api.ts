const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchMe(token: string) {
  const res = await fetch(`${API_URL}/api/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_URL}/api/v1/health`);
  return res.json();
}
