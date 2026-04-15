const AUTH_COOKIE_NAME = "sg_session";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

export function setAuthSession(username: string) {
  if (typeof document === "undefined") return;
  const value = encodeURIComponent(username || "user");
  document.cookie = `${AUTH_COOKIE_NAME}=${value}; Path=/; Max-Age=${AUTH_COOKIE_MAX_AGE}; SameSite=Lax`;
}

export function clearAuthSession() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function isAuthenticated(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((cookie) => cookie.startsWith(`${AUTH_COOKIE_NAME}=`));
}

export const AUTH_COOKIE = AUTH_COOKIE_NAME;
