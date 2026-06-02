import { launch } from "cloakbrowser";
import { spawn, execSync } from "child_process";
import http from "http";
import fs from "fs";
import { setTimeout as wait } from "timers/promises";

const VNC_PORT = 5901;
const NOVNC_PORT = 6082;
const DISPLAY = ":99";
const API_PORT = 6100;
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

let platform = process.argv.includes("--platform") ? process.argv[process.argv.indexOf("--platform") + 1] : "gmail";
const email = process.argv.includes("--email") ? process.argv[process.argv.indexOf("--email") + 1] : null;
let accountId = process.argv.includes("--account-id") ? process.argv[process.argv.indexOf("--account-id") + 1] : null;
const isDesktop = process.argv.includes("--desktop");

let cfg = PLATFORMS[platform] || PLATFORMS.gmail;

process.env.DISPLAY = DISPLAY;

let browser = null;
let page = null;
let ctx = null;
let loginDetected = false;
let xvfbProcess = null;
let x11vncProcess = null;
let novncProcess = null;

// Process cleanup on exit
function cleanup() {
  console.log("[CLEANUP] Shutting down processes...");
  
  if (browser) {
    try {
      browser.close().catch(() => {});
      console.log("[CLEANUP] Browser closed");
    } catch (e) {
      console.error("[CLEANUP] Error closing browser:", e.message);
    }
  }
  
  [xvfbProcess, x11vncProcess, novncProcess].forEach(proc => {
    if (proc) {
      try {
        proc.kill();
        console.log("[CLEANUP] Process killed");
      } catch (e) {
        console.error("[CLEANUP] Error killing process:", e.message);
      }
    }
  });
  
  // Try to kill any remaining cloakbrowser/chromium processes
  try {
    execSync("pkill -f cloakbrowser/chrom", { stdio: "ignore" });
  } catch (e) {
    // Ignore if no processes found
  }
}

// Better error handling wrapper
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

// Ensure cookies directory exists
function ensureCookieDir() {
  try {
    if (!fs.existsSync("cookies")) {
      fs.mkdirSync("cookies", { recursive: true });
    }
  } catch (e) {
    console.error("[ERROR] Failed to create cookies directory:", e.message);
  }
}

async function doCapture() {
  if (!ctx) return null;
  try {
    const cookies = await ctx.cookies();
    const platformDomain = platform === "gmail" ? "google" : platform;
    const filtered = cookies.filter(c => c.domain?.includes(platformDomain) || c.name === platform);
    const file = getCookieFile();
    fs.writeFileSync(file, JSON.stringify(filtered, null, 2));
    loginDetected = true;
    console.log(`[AUTO] ${platform} login detected! Captured ${filtered.length} cookies -> ${file}`);
    return filtered.length;
  } catch (error) {
    console.error("[ERROR] Failed to capture cookies:", error.message);
    return null;
  }
}

async function waitForLogin() {
  let checkCount = 0;
  while (!loginDetected) {
    await wait(2000);
    checkCount++;
    try {
      // Check if page still exists
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
      const hasAuth = cookies.some(c => cfg.authCookies.includes(c.name));

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
      // Continue waiting unless it's a critical error
      if (checkCount > 200) { // Extended timeout for error cases
        console.log("[WAIT] Too many errors, stopping wait");
        break;
      }
    }
  }
}

function start(cmd, args) {
  const p = spawn(cmd, args, { stdio: "pipe", env: { ...process.env, DISPLAY } });
  p.stdout.on("data", d => process.stdout.write(`[${cmd}] ${d}`));
  p.stderr.on("data", d => process.stderr.write(`[${cmd}] ${d}`));
  return p;
}

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
        const newPlatform = url.searchParams.get("platform") || platform;
        const newAccountId = url.searchParams.get("account_id") || null;
        if (page) {
          platform = newPlatform;
          if (newAccountId) accountId = newAccountId;
          cfg = PLATFORMS[platform] || PLATFORMS.gmail;
          loginDetected = false;
          await page.goto(target, { timeout: 30000, waitUntil: "load" });
          waitForLogin();
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true, url: target, platform }));
        } else {
          res.writeHead(400);
          res.end(JSON.stringify({ success: false, error: "No page" }));
        }
      } else if (url.pathname === "/status") {
        const file = getCookieFile();
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          running: !!browser,
          pageLoaded: !!page && !page.isClosed(),
          loginDetected,
          platform,
          cookiesFile: fs.existsSync(file) ? file : null,
          vncUrl: `http://153.75.247.117:${NOVNC_PORT}/vnc.html`,
        }));
      } else {
        res.writeHead(200);
        res.end("VNC social login helper is running.");
      }
    } catch (error) {
      console.error("[API] Error handling request:", error.message);
      res.writeHead(500);
      res.end(JSON.stringify({ success: false, error: "Internal server error" }));
    }
  });
  server.listen(API_PORT, "0.0.0.0");
  console.log(`VNC API listening on port ${API_PORT}`);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
process.on("exit", cleanup);

ensureCookieDir();

// Start virtual display
console.log("[START] Starting Xvfb...");
xvfbProcess = start("Xvfb", [DISPLAY, "-screen", "0", "1280x800x24"]);
await wait(2000);

// Start VNC server
console.log("[START] Starting x11vnc...");
x11vncProcess = start("x11vnc", ["-display", DISPLAY, "-forever", "-nopw", "-rfbport", String(VNC_PORT)]);
await wait(2000);

// Start noVNC proxy
console.log("[START] Starting noVNC proxy...");
novncProcess = start("bash", ["/opt/noVNC/utils/novnc_proxy", "--vnc", `localhost:${VNC_PORT}`, "--listen", String(NOVNC_PORT)]);
await wait(3000);

// Start API server
startApi();
console.log(`\n========================================`);
console.log(`VNC SOCIAL LOGIN HELPER`);
console.log(`Platform: ${platform}`);
console.log(`Viewport: ${isDesktop ? "Desktop" : `Mobile (${MOBILE_VIEWPORT.width}x${MOBILE_VIEWPORT.height})`}`);
console.log(`VNC:  http://153.75.247.117:${NOVNC_PORT}/vnc.html`);
console.log(`API:  http://localhost:${API_PORT}`);
if (accountId) console.log(`Account: ${accountId}`);
console.log(`========================================\n`);

try { 
  execSync("pkill -f cloakbrowser/chrom", { stdio: "ignore" }); 
} catch(e) {
  // Ignore if no processes found
}

console.log("Launching CloakBrowser on display " + DISPLAY);
try {
  browser = await withErrorHandling(
    () => launch({ 
      headless: false, 
      args: [
        "--no-sandbox", 
        "--disable-setuid-sandbox", 
        "--disable-dev-shm-usage", 
        "--single-process",
        "--disable-gpu"
      ]
    }), 
    "Browser launch"
  );
} catch (error) {
  console.error("[FATAL] Failed to launch browser:", error.message);
  cleanup();
  process.exit(1);
}

try {
  const ctxOpts = isDesktop ? {} : { viewport: MOBILE_VIEWPORT, isMobile: true };
  ctx = await withErrorHandling(
    () => browser.newContext(ctxOpts), 
    "Creating browser context"
  );
  
  page = await withErrorHandling(
    () => ctx.newPage(), 
    "Creating new page"
  );
} catch (error) {
  console.error("[FATAL] Failed to initialize browser context:", error.message);
  if (browser) {
    try { await browser.close(); } catch(e) {}
  }
  cleanup();
  process.exit(1);
}

let loginUrl = cfg.loginUrl;
if (platform === "gmail" && email) {
  loginUrl = `https://accounts.google.com/signin/v2/identifier?Email=${encodeURIComponent(email)}&flowName=GlifWebSignIn&flowEntry=ServiceLogin`;
}

console.log(`Navigating to ${platform} login...`);
try {
  await withErrorHandling(
    () => page.goto(loginUrl, { timeout: 30000, waitUntil: "load" }), 
    "Navigating to login page"
  );
  console.log(`${platform} login page loaded in VNC. Waiting for login...`);
} catch (error) {
  console.error("[FATAL] Failed to navigate to login page:", error.message);
  cleanup();
  process.exit(1);
}

// Start waiting for login in background
waitForLogin().then(() => {
  console.log("\n========================================");
  console.log(`${platform.toUpperCase()} LOGIN DETECTED - Cookies auto-captured!`);
  console.log(`File: ${getCookieFile()}`);
  console.log("VNC browser kept open. Close this process to stop.");
  console.log("========================================\n");
}).catch(error => {
  console.error("[ERROR] Wait for login failed:", error.message);
});

// Keep the process running
await new Promise(() => {});
