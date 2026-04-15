const API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "";

export async function fetchAnalyticsSummary() {
  const res = await fetch(`${API_URL}/api/analytics/summary`, {
    cache: "no-store", // We want real-time stats
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch analytics summary: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchAccounts() {
  const res = await fetch(`${API_URL}/api/accounts`, {
    cache: "no-store", // Always fetch the latest accounts
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch accounts: ${res.statusText}`);
  }

  return res.json();
}

export async function createAccount(data: { platform: string; username: string; session_data?: string }) {
  const res = await fetch(`${API_URL}/api/accounts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Failed to create account: ${res.statusText}`);
  }

  return res.json();
}
