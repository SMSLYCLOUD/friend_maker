import { chromium } from "playwright-core";
import http from "http";
import fs from "fs";
import { setTimeout as wait } from "timers/promises";

const KASM_PORT = parseInt(process.env.KASM_PORT || "6901", 10);
const API_PORT = 6100;
const CDP_ENDPOINT = process.env.CDP_ENDPOINT || "http://localhost:9222";
const MOBILE_VIEWPORT = { width: 390, height: 844 };

const PLATFORMS = {
  instagram: {
    loginUrl: "https://www.instagram.com/accounts/login/",
    loginPaths: ["accounts/login", "accounts/onetap"],
    authCookies: ["sessionid", "ds_user_id", "csrftoken"],
  },
  twitter: {
    loginUrl: "https://twitter.com/i/flow/login",
    loginPaths: ["i/flow/login", "login"],
    authCookies: ["auth_token", "twid", "ct0"],
  },
  facebook: {
    loginUrl: "https://www.facebook.com/login",
    loginPaths: ["login", "checkpoint"],
    authCookies: ["c_user", "xs", "sb"],
  },
  linkedin: {
    loginUrl: "https://www.linkedin.com/login",
    loginPaths: ["login", "checkpoint"],
    authCookies: ["li_at", "JSESSIONID"],
  },
  tiktok: {
    loginUrl: "https://www.tiktok.com/login/phone-or-email/email",
    loginPaths: ["login"],
    authCookies: ["sessionid", "sid_tt", "passport_csrf_token"],
  },
  substack: {
    loginUrl: "https://substack.com/sign-in",
    loginPaths: ["sign-in"],
    authCookies: ["substack.sid"],
  },
  gmail: {
    loginUrl: "https://accounts.google.com/signin",
    loginPaths: ["signin", "ServiceLogin", "identifier", "challenge"],
    authCookies: ["SAPISID", "SSID", "OSID", "SID", "HSID"],
  },
};

let platform = process.argv.includes("--platform") ? process.argv[process.argv.indexOf("--platform") + 1] : null;
const email = process.argv.includes("--email") ? process.argv[process.argv.indexOf("--email") + 1] : null;
let accountId = process.argv.includes("--account-id") ? process.argv[process.argv.indexOf("--account-id") + 1] : null;
const isDesktop = !process.argv.includes("--mobile");

let cfg = platform ? (PLATFORMS[platform] || PLATFORMS.gmail) : null;

let browser = null;
let page = null;
let ctx = null;
let loginDetected = false;

// ── Cleanup ──────────────────────────────────────────────────
function cleanup() {
  console.log("[CLEANUP] Shutting down...");
  if (browser) {
    browser.close().catch(() => {});
  }
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
process.on("exit", cleanup);

// ── Helpers ──────────────────────────────────────────────────
async function withErrorHandling(fn, operationName) {
  try {
    return await fn();
  } catch (error) {
    console.error(`[ERROR] ${operationName} failed:`, error.message);
    throw error;
  }
}

function getCookieFile() {
  const prefix = accountId || platform;
  return `cookies/${prefix}_cookies.json`;
}

function ensureCookieDir() {
  try {
    if (!fs.existsSync("cookies")) {
      fs.mkdirSync("cookies", { recursive: true });
    }
  } catch (e) {
    console.error("[ERROR] Failed to create cookies directory:", e.message);
  }
}

// ── Cookie capture ───────────────────────────────────────────
async function doCapture() {
  if (!ctx) return null;
  try {
    const cookies = await ctx.cookies();
    const platformDomain = platform === "gmail" ? "google" : platform;
    const filtered = cookies.filter(c => {
      const d = (c.domain || "").toLowerCase();
      return d.includes(platformDomain) || d.includes(`${platformDomain}.com`) || d.includes(`.${platformDomain}.`);
    });
    const file = getCookieFile();
    fs.writeFileSync(file, JSON.stringify(filtered.length ? filtered : cookies, null, 2));
    loginDetected = true;
    console.log(`[AUTO] ${platform} login detected! Captured ${filtered.length || cookies.length} cookies -> ${file}`);
    return filtered.length || cookies.length;
  } catch (error) {
    console.error("[ERROR] Failed to capture cookies:", error.message);
    return null;
  }
}

// ── Login detection ──────────────────────────────────────────
async function waitForLogin() {
  if (!cfg) {
    console.log("[WAIT] No platform config, skipping login detection");
    return;
  }
  let checkCount = 0;
  while (!loginDetected) {
    await wait(2000);
    checkCount++;
    try {
      if (!page || page.isClosed()) {
        console.log("[WAIT] Page is closed, stopping wait");
        break;
      }

      const currentUrl = page.url();
      const isStillOnLogin = cfg.loginPaths.some(p => currentUrl.includes(p));
      const isOnPlatform = currentUrl.includes(`${platform}.com`) || currentUrl.includes("google.com");
      const navigatedAway = !isStillOnLogin && isOnPlatform;
      const timedOut = checkCount > 150;

      const cookies = await ctx.cookies();
      const platformDomain = platform === "gmail" ? "google" : platform;
      const hasAuth = cookies.some(c => {
        const d = (c.domain || "").toLowerCase();
        return cfg.authCookies.includes(c.name) || d.includes(platformDomain);
      });

      if (hasAuth) {
        await doCapture();
        break;
      }

      if (navigatedAway || timedOut) {
        if (timedOut) {
          console.log(`[WAIT] Timed out. URL: ${currentUrl}`);
        }
        break;
      }
    } catch (error) {
      console.error("[WAIT] Error checking login status:", error.message);
      if (checkCount > 200) {
        console.log("[WAIT] Too many errors, stopping wait");
        break;
      }
    }
  }
}

// ── API server ───────────────────────────────────────────────
function startApi() {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");

      if (url.pathname === "/capture") {
        const count = await doCapture();
        if (count !== null) {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true, file: getCookieFile(), count, platform }));
        } else {
          res.writeHead(400);
          res.end(JSON.stringify({ success: false, error: "No browser context" }));
        }

      } else if (url.pathname === "/navigate" && url.searchParams.has("url")) {
        const target = url.searchParams.get("url");
        const newPlatform = url.searchParams.get("platform");
        const newAccountId = url.searchParams.get("account_id") || null;

        if (!page || page.isClosed()) {
          res.writeHead(400);
          res.end(JSON.stringify({ success: false, error: "No page" }));
          return;
        }

        try {
          if (newPlatform) {
            platform = newPlatform;
            cfg = PLATFORMS[platform] || null;
          }
          if (newAccountId) accountId = newAccountId;
          loginDetected = false;
          await page.goto(target, { timeout: 30000, waitUntil: "load" });
          waitForLogin().catch(e => console.error("[navigate] waitForLogin error:", e.message));
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true, url: target, platform }));
        } catch (navError) {
          console.error(`[navigate] goto failed for ${target}:`, navError.message);
          res.writeHead(500);
          res.end(JSON.stringify({ success: false, error: navError.message }));
        }

      } else if (url.pathname === "/status") {
        const file = getCookieFile();
        const hostIp = process.env.HOST_IP || "localhost";
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          running: !!browser,
          pageLoaded: !!page && !page.isClosed(),
          loginDetected,
          platform,
          cookiesFile: fs.existsSync(file) ? file : null,
          kasmUrl: `http://${hostIp}:${KASM_PORT}`,
        }));

      } else {
        res.writeHead(200);
        res.end("Kasm login helper is running.");
      }
    } catch (error) {
      console.error("[API] Error handling request:", error.message);
      res.writeHead(500);
      res.end(JSON.stringify({ success: false, error: "Internal server error" }));
    }
  });

  server.listen(API_PORT, "0.0.0.0");
  console.log(`Kasm login API listening on port ${API_PORT}`);
}

// ── Main ─────────────────────────────────────────────────────
ensureCookieDir();

// Start the API server first so the backend can reach us immediately
startApi();

console.log("[START] Waiting for Chrome CDP endpoint...");

// Chrome starts after the Kasm display scripts run, so retry until it's ready
const MAX_RETRIES = 90; // 90 × 2s = 3 minutes
for (let i = 0; i < MAX_RETRIES; i++) {
  try {
    browser = await chromium.connectOverCDP(CDP_ENDPOINT, { timeout: 5000 });
    console.log("[START] Connected to Chrome via CDP");
    break;
  } catch (e) {
    console.log(`[START] Chrome not ready yet (attempt ${i + 1}/${MAX_RETRIES}), retrying in 2s...`);
    await wait(2000);
  }
}

if (!browser) {
  console.error("[FATAL] Chrome CDP endpoint not available after 3 minutes");
  process.exit(1);
}

// Get or create a browser context
const contexts = browser.contexts();
if (contexts.length > 0) {
  ctx = contexts[0];
  const pages = ctx.pages();
  page = pages.length > 0 ? pages[0] : await ctx.newPage();
} else {
  ctx = await browser.newContext(
    isDesktop ? {} : { viewport: MOBILE_VIEWPORT, isMobile: true }
  );
  page = await ctx.newPage();
}

const hostIp = process.env.HOST_IP || "localhost";
console.log(`\n========================================`);
console.log(`KASM SOCIAL LOGIN HELPER`);
console.log(`Platform: ${platform || "auto (set via API)"}`);
console.log(`Viewport: ${isDesktop ? "Desktop" : `Mobile (${MOBILE_VIEWPORT.width}x${MOBILE_VIEWPORT.height})`}`);
console.log(`Kasm: http://${hostIp}:${KASM_PORT}`);
console.log(`API:  http://${hostIp}:${API_PORT}`);
if (accountId) console.log(`Account: ${accountId}`);
console.log(`========================================\n`);

// Start on blank page — platform navigation happens via API call from backend
console.log("Starting on about:blank — waiting for backend /navigate API call...");
try {
  await page.goto("about:blank", { timeout: 10000 });
} catch (error) {
  console.warn("[WARN] Failed to load blank page:", error.message);
}

// Keep the process running
await new Promise(() => {});
