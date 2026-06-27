import { launch } from "cloakbrowser";
import { spawn, execSync } from "child_process";
import http from "http";
import fs from "fs";

const VNC_PORT = 5901;
const NOVNC_PORT = 6082;
const DISPLAY = ":100";
const API_PORT = 6100;

const email = process.argv.includes("--email") ? process.argv[process.argv.indexOf("--email") + 1] : null;
const accountId = process.argv.includes("--account-id") ? process.argv[process.argv.indexOf("--account-id") + 1] : null;

process.env.DISPLAY = DISPLAY;

let browser, page, ctx;
let loginDetected = false;

function getCookieFile() {
  return accountId
    ? `cookies/gmail_${accountId}_cookies.json`
    : "cookies/gmail_vnc_cookies.json";
}

async function doCapture() {
  if (!ctx) return null;
  const cookies = await ctx.cookies();
  const gmailCookies = cookies.filter(c => c.domain?.includes("google"));
  const file = getCookieFile();
  fs.writeFileSync(file, JSON.stringify(gmailCookies, null, 2));
  loginDetected = true;
  console.log(`[AUTO] Login detected! Captured ${gmailCookies.length} Google cookies -> ${file}`);
  return gmailCookies;
}

async function waitForLogin() {
  const loginDomains = ["accounts.google.com", "signin", "ServiceLogin", "identifier", "challenge", "password"];
  const loggedInDomains = ["mail.google.com", "myaccount.google.com", "google.com/mail", "inbox"];
  let checkCount = 0;
  while (!loginDetected) {
    await new Promise(r => setTimeout(r, 2000));
    checkCount++;
    try {
      const currentUrl = page.url();
      const isStillOnLogin = loginDomains.some(d => currentUrl.includes(d));
      const isOnService = loggedInDomains.some(d => currentUrl.includes(d));
      const isGoogle = currentUrl.includes("google.com");

      if ((!isStillOnLogin && isGoogle) || isOnService || checkCount > 150) {
        const cookies = await ctx.cookies();
        const gmailCookies = cookies.filter(c => c.domain?.includes("google"));
        const hasAuth = gmailCookies.some(c => ["SAPISID", "SSID", "OSID", "SID", "HSID"].includes(c.name));
        if (hasAuth) {
          await doCapture();
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
      if (count) {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ success: true, file: getCookieFile(), count }));
      } else {
        res.writeHead(400);
        res.end(JSON.stringify({ success: false, error: "No browser context" }));
      }
    } else if (url.pathname === "/navigate" && url.searchParams.has("url")) {
      const target = url.searchParams.get("url");
      if (page) {
        await page.goto(target, { timeout: 30000, waitUntil: "load" });
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ success: true, url: target }));
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
        cookiesFile: fs.existsSync(file) ? file : null,
        vncUrl: `http://${process.env.HOST_IP || 'localhost'}:${NOVNC_PORT}/vnc.html`,
      }));
    } else {
      res.writeHead(200);
      res.end("VNC Gmail login helper is running.");
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

start("/opt/noVNC/utils/novnc_proxy", ["--vnc", `localhost:${VNC_PORT}`, "--listen", String(NOVNC_PORT), "--web", "/opt/noVNC"]);
await new Promise(r => setTimeout(r, 3000));

startApi();
console.log(`\n========================================`);
console.log(`VNC GMAIL LOGIN HELPER`);
console.log(`VNC:  http://${process.env.HOST_IP || 'localhost'}:${NOVNC_PORT}/vnc.html`);
console.log(`API:  http://localhost:${API_PORT}`);
if (accountId) console.log(`Account: ${accountId}`);
console.log(`========================================\n`);

try { execSync("pkill -f cloakbrowser/chrom"); } catch(e) {}

console.log("Launching CloakBrowser on display " + DISPLAY);
browser = await launch({ headless: false, args: ["--no-sandbox", "--disable-gpu"] });

ctx = await browser.newContext();
page = await ctx.newPage();

const loginUrl = email
  ? `https://accounts.google.com/signin/v2/identifier?Email=${encodeURIComponent(email)}&flowName=GlifWebSignIn&flowEntry=ServiceLogin`
  : "https://accounts.google.com/signin";

console.log("Navigating to Google sign-in...");
await page.goto(loginUrl, { timeout: 30000, waitUntil: "load" });
console.log("Google login page loaded in VNC. Waiting for login...");

waitForLogin().then(() => {
  console.log("\n========================================");
  console.log("LOGIN DETECTED - Cookies auto-captured!");
  console.log(`File: ${getCookieFile()}`);
  console.log("VNC browser kept open. Close this process to stop.");
  console.log("========================================\n");
});

await new Promise(() => {});
