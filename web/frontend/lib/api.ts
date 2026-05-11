const IS_SERVER = typeof window === "undefined";
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || "http://python-backend:8000";
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "";
// Ensure we don't have a trailing slash or /api suffix
const CLEAN_API_URL = PUBLIC_API_URL.replace(/\/api\/?$/, "").replace(/\/$/, "");

const API_URL = IS_SERVER ? INTERNAL_API_URL : (CLEAN_API_URL || "http://localhost:8010");

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

export async function login(credentials: { username: string, password: string }) {
  const res = await fetch(`${API_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed: ${res.statusText}`);
  }

  return res.json();
}

export async function register(credentials: { username: string, password: string }) {
  const res = await fetch(`${API_URL}/api/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Registration failed: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchCampaigns() {
  const res = await fetch(`${API_URL}/api/campaigns`, {
    headers: defaultHeaders,
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch campaigns");
  return res.json();
}

export async function createCampaign(data: any) {
  const res = await fetch(`${API_URL}/api/campaigns`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create campaign");
  return res.json();
}

export async function startCampaign(id: string) {
  const res = await fetch(`${API_URL}/api/campaigns/${id}/start`, {
    method: "POST",
    headers: defaultHeaders,
  });
  if (!res.ok) throw new Error("Failed to start campaign");
  return res.json();
}

export async function stopCampaign(id: string) {
  const res = await fetch(`${API_URL}/api/campaigns/${id}/stop`, {
    method: "POST",
    headers: defaultHeaders,
  });
  if (!res.ok) throw new Error("Failed to stop campaign");
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_URL}/api/settings`, {
    headers: defaultHeaders,
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(data: any) {
  const res = await fetch(`${API_URL}/api/settings`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}
