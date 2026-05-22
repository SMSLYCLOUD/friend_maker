import { launch } from "cloakbrowser";
import { spawn, execSync } from "child_process";
import http from "http";
import fs from "fs";

const VNC_PORT = 5901;
const NOVNC_PORT = 6082;
const DISPLAY = ":100";
const API_PORT = 6100;

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
    authCookies: ["sessionid", "sid_tt"],
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

let cfg = PLATFORMS[platform] || PLATFORMS.gmail;

process.env.DISPLAY = DISPLAY;

let browser, page, ctx;
let loginDetected = false;

function getCookieFile() {
  const prefix = accountId || platform;
  return `cookies/${prefix}_cookies.json`;
}

async function doCapture() {
  if (!ctx) return null;
  const cookies = await ctx.cookies();
  const platformDomain = platform === "gmail" ? "google" : platform;
  const filtered = cookies.filter(c => c.domain?.includes(platformDomain) || c.name === platform);
  const file = getCookieFile();
  fs.writeFileSync(file, JSON.stringify(filtered, null, 2));
  loginDetected = true;
  console.log(`[AUTO] ${platform} login detected! Captured ${filtered.length} cookies -> ${file}`);
  return filtered.length;
}

async function waitForLogin() {
  let checkCount = 0;
  while (!loginDetected) {
    await new Promise(r => setTimeout(r, 2000));
    checkCount++;
    try {
      const currentUrl = page.url();
      const isStillOnLogin = cfg.loginPaths.some(p => currentUrl.includes(p));
      const isOnPlatform = currentUrl.includes(`${platform}.com`) || currentUrl.includes("google.com");
      const navigatedAway = !isStillOnLogin && isOnPlatform;
      const timedOut = checkCount > 150;

      if (navigatedAway || timedOut) {
        const cookies = await ctx.cookies();
        const hasAuth = cookies.some(c => cfg.authCookies.includes(c.name));
        if (hasAuth || timedOut) {
          if (hasAuth) await doCapture();
          break;
        }
      }
    } catch (e) {}
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
        pageLoaded: !!page,
        loginDetected,
        platform,
        cookiesFile: fs.existsSync(file) ? file : null,
        vncUrl: `http://153.75.247.117:${NOVNC_PORT}/vnc.html`,
      }));
    } else {
      res.writeHead(200);
      res.end("VNC social login helper is running.");
    }
  });
  server.listen(API_PORT, "0.0.0.0");
  console.log(`VNC API listening on port ${API_PORT}`);
}

process.on("SIGINT", () => process.exit());
process.on("SIGTERM", () => process.exit());

start("Xvfb", [DISPLAY, "-screen", "0", "1280x800x24"]);
await new Promise(r => setTimeout(r, 2000));

start("x11vnc", ["-display", DISPLAY, "-forever", "-nopw", "-rfbport", String(VNC_PORT)]);
await new Promise(r => setTimeout(r, 2000));

start("/root/noVNC/utils/novnc_proxy", ["--vnc", `localhost:${VNC_PORT}`, "--listen", String(NOVNC_PORT)]);
await new Promise(r => setTimeout(r, 3000));

startApi();
console.log(`\n========================================`);
console.log(`VNC SOCIAL LOGIN HELPER`);
console.log(`Platform: ${platform}`);
console.log(`VNC:  http://153.75.247.117:${NOVNC_PORT}/vnc.html`);
console.log(`API:  http://localhost:${API_PORT}`);
if (accountId) console.log(`Account: ${accountId}`);
console.log(`========================================\n`);

try { execSync("pkill -f cloakbrowser/chrom"); } catch(e) {}

console.log("Launching CloakBrowser on display " + DISPLAY);
browser = await launch({ headless: false, args: ["--no-sandbox", "--disable-gpu"] });

ctx = await browser.newContext();
page = await ctx.newPage();

let loginUrl = cfg.loginUrl;
if (platform === "gmail" && email) {
  loginUrl = `https://accounts.google.com/signin/v2/identifier?Email=${encodeURIComponent(email)}&flowName=GlifWebSignIn&flowEntry=ServiceLogin`;
}

console.log(`Navigating to ${platform} login...`);
await page.goto(loginUrl, { timeout: 30000, waitUntil: "load" });
console.log(`${platform} login page loaded in VNC. Waiting for login...`);

waitForLogin().then(() => {
  console.log("\n========================================");
  console.log(`${platform.toUpperCase()} LOGIN DETECTED - Cookies auto-captured!`);
  console.log(`File: ${getCookieFile()}`);
  console.log("VNC browser kept open. Close this process to stop.");
  console.log("========================================\n");
});

await new Promise(() => {});
