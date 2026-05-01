const API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "";
// Fallback key matches backend config. In production this should be managed via env.
const API_KEY = process.env.API_KEY || "super-secret-api-key";

const defaultHeaders = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

export async function fetchAnalyticsSummary() {
  const res = await fetch(`${API_URL}/api/analytics/summary`, {
    cache: "no-store", // We want real-time stats
    headers: defaultHeaders,
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch analytics summary: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchAccounts() {
  const res = await fetch(`${API_URL}/api/accounts`, {
    cache: "no-store", // Always fetch the latest accounts
    headers: defaultHeaders,
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch accounts: ${res.statusText}`);
  }

  return res.json();
}

export async function createAccount(data: { platform: string; username: string; session_data?: string }) {
  const res = await fetch(`${API_URL}/api/accounts`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Failed to create account: ${res.statusText}`);
  }

  return res.json();
}
