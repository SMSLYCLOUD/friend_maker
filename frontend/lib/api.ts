import { getToken } from "./auth";

const IS_SERVER = typeof window === "undefined";
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || "http://python-backend:8000";
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "";
const CLEAN_API_URL = PUBLIC_API_URL.replace(/\/api\/?$/, "").replace(/\/$/, "");
const API_URL = IS_SERVER ? INTERNAL_API_URL : (CLEAN_API_URL || "http://localhost:8000");

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (!IS_SERVER) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

export async function fetchAnalyticsSummary() {
  const res = await fetch(`${API_URL}/api/analytics/summary`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch analytics: ${res.statusText}`);
  return res.json();
}

export async function fetchAccounts() {
  const res = await fetch(`${API_URL}/api/accounts`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch accounts: ${res.statusText}`);
  return res.json();
}

export async function createAccount(data: { platform: string; username: string; password?: string }) {
  const res = await fetch(`${API_URL}/api/accounts`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create account: ${res.statusText}`);
  return res.json();
}

export async function login(credentials: { username: string; password: string }) {
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

export async function register(credentials: { username: string; password: string }) {
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
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch campaigns");
  return res.json();
}

export async function createCampaign(data: any) {
  const res = await fetch(`${API_URL}/api/campaigns`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create campaign");
  return res.json();
}

export async function startCampaign(id: string) {
  const res = await fetch(`${API_URL}/api/campaigns/${id}/start`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to start campaign");
  return res.json();
}

export async function stopCampaign(id: string) {
  const res = await fetch(`${API_URL}/api/campaigns/${id}/stop`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to stop campaign");
  return res.json();
}

export async function deleteCampaign(id: string) {
  const res = await fetch(`${API_URL}/api/campaigns/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete campaign");
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_URL}/api/settings`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function triggerEmailCampaign() {
  const res = await fetch(`${API_URL}/api/email-campaign/trigger`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to trigger email campaign");
  return res.json();
}

export async function triggerPlatform(platform: string, zip_code?: string, business_type?: string) {
  const params = new URLSearchParams();
  if (zip_code) params.set("zip_code", zip_code);
  if (business_type) params.set("business_type", business_type);
  const qs = params.toString();
  const res = await fetch(`${API_URL}/api/platforms/${platform}/trigger${qs ? `?${qs}` : ""}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to trigger ${platform}`);
  return res.json();
}

export async function triggerAllPlatforms() {
  const res = await fetch(`${API_URL}/api/platforms/trigger-all`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to trigger all platforms");
  return res.json();
}

export async function fetchPlatforms() {
  const res = await fetch(`${API_URL}/api/platforms`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch platforms");
  return res.json();
}

export async function updateSettings(data: any) {
  const res = await fetch(`${API_URL}/api/settings`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

export async function updateEnvVars(data: Record<string, string>) {
  const res = await fetch(`${API_URL}/api/settings/env`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to update env vars");
  }
  return res.json();
}

export async function fetchEnvVars() {
  const res = await fetch(`${API_URL}/api/settings/env`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch env vars");
  return res.json();
}

export async function fetchGlobalSettings() {
  const res = await fetch(`${API_URL}/api/settings/admin`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch global settings");
  return res.json();
}

export async function updateGlobalSettings(data: any) {
  const res = await fetch(`${API_URL}/api/settings/admin`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update global settings");
  return res.json();
}

export async function kasmLogin(accountId: string) {
  const res = await fetch(`${API_URL}/api/accounts/${accountId}/kasm-login`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start Kasm login");
  }
  return res.json();
}

export async function kasmSessionStatus(accountId: string) {
  const res = await fetch(`${API_URL}/api/accounts/${accountId}/kasm-session-status`, {
    headers: authHeaders(),
  });
  if (!res.ok) return { login_detected: false, has_session: false, cookies_available: false };
  return res.json();
}

export async function captureCookies(accountId: string) {
  const res = await fetch(`${API_URL}/api/accounts/${accountId}/capture-cookies`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to capture cookies");
  }
  return res.json();
}

export async function deleteAccount(id: string) {
  const res = await fetch(`${API_URL}/api/accounts/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete account");
  return res.json();
}

export async function fetchActivityFeed() {
  const res = await fetch(`${API_URL}/api/analytics/activity-feed`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch activity feed");
  return res.json();
}

export async function fetchAudienceInsights() {
  const res = await fetch(`${API_URL}/api/analytics/audience-insights`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch audience insights");
  return res.json();
}

export async function fetchBotImages() {
  const res = await fetch(`${API_URL}/api/settings/images`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch images");
  return res.json();
}

export async function uploadBotImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/settings/upload-image`, {
    method: "POST",
    headers: { Authorization: authHeaders()["Authorization"] || "" },
    body: form,
  });
  if (!res.ok) throw new Error("Failed to upload image");
  return res.json();
}

export async function deleteBotImage(filename: string) {
  const res = await fetch(`${API_URL}/api/settings/images/${filename}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete image");
  return res.json();
}

export function getImageUrl(filename: string) {
  return `${API_URL}/api/settings/images/${filename}`;
}

// --- Templates ---

export async function fetchTemplates(templateType?: string) {
  const qs = templateType ? `?template_type=${encodeURIComponent(templateType)}` : "";
  const res = await fetch(`${API_URL}/api/templates${qs}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch templates");
  return res.json();
}

export async function createTemplate(data: { name: string; content: string; template_type: string; platform?: string; is_default?: boolean }) {
  const res = await fetch(`${API_URL}/api/templates`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create template");
  }
  return res.json();
}

export async function updateTemplate(id: string, data: Record<string, any>) {
  const res = await fetch(`${API_URL}/api/templates/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update template");
  return res.json();
}

export async function deleteTemplate(id: string) {
  const res = await fetch(`${API_URL}/api/templates/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete template");
  return res.json();
}


export async function fetchProviderStatus() {
  const res = await fetch(`${API_URL}/api/providers/status`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch provider status");
  return res.json();
}

export async function rotateProvider(provider: string) {
  const res = await fetch(`${API_URL}/api/providers/rotate`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) throw new Error("Failed to rotate provider");
  return res.json();
}
