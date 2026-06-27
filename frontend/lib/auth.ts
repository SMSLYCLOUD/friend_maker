const AUTH_COOKIE_NAME = "sg_session";
const TOKEN_COOKIE_NAME = "sg_token";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export function setAuthSession(username: string, token: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=${encodeURIComponent(username)}; Path=/; Max-Age=${AUTH_COOKIE_MAX_AGE}; SameSite=Lax`;
  document.cookie = `${TOKEN_COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; Max-Age=${AUTH_COOKIE_MAX_AGE}; SameSite=Lax`;
}

export function clearAuthSession() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
  document.cookie = `${TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function isAuthenticated(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((cookie) => cookie.startsWith(`${AUTH_COOKIE_NAME}=`));
}

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const AUTH_COOKIE = AUTH_COOKIE_NAME;
