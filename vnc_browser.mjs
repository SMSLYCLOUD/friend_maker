import { launch } from "cloakbrowser";
import { spawn, execSync } from "child_process";
import http from "http";

const VNC_PORT = 5900;
const NOVNC_PORT = 6081;
const DISPLAY = ":99";
const API_PORT = 6099;
const targetUrl = process.argv.includes("--url") ? process.argv[process.argv.indexOf("--url") + 1] : null;
const defaultUrl = targetUrl || "https://www.tiktok.com/login/phone-or-email/email";

process.env.DISPLAY = DISPLAY;

let browser, page, ctx;
let cookieTimer = null;

function start(cmd, args) {
  const p = spawn(cmd, args, { stdio: "pipe", env: { ...process.env, DISPLAY } });
  p.stdout.on("data", d => process.stdout.write(`[${cmd}] ${d}`));
  p.stderr.on("data", d => process.stderr.write(`[${cmd}] ${d}`));
  return p;
}

// HTTP server for cookie capture signal
function startApi() {
  const server = http.createServer(async (req, res) => {
    if (req.url.startsWith("/capture")) {
      const platform = new URL(req.url, "http://localhost").searchParams.get("platform") || "unknown";
      if (ctx) {
        const cookies = await ctx.cookies();
        const fs = await import("fs");
        const file = `cookies/${platform}_cookies.json`;
        fs.writeFileSync(file, JSON.stringify(cookies, null, 2));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ success: true, file, count: cookies.length }));
      } else {
        res.writeHead(400);
        res.end(JSON.stringify({ success: false, error: "No browser context" }));
      }
    } else {
      res.writeHead(200);
      res.end("VNC browser is running");
    }
  });
  server.listen(API_PORT, "0.0.0.0");
}

process.on("SIGINT", () => process.exit());
process.on("SIGTERM", () => process.exit());
process.on("SIGUSR1", async () => {
  if (ctx) {
    const fs = await import("fs");
    const cookies = await ctx.cookies();
    fs.writeFileSync("cookies/vnc_cookies.json", JSON.stringify(cookies, null, 2));
    console.log("\n[VNC] Cookies captured via SIGUSR1 -> cookies/vnc_cookies.json");
  }
});

start("Xvfb", [DISPLAY, "-screen", "0", "1280x800x24"]);
await new Promise(r => setTimeout(r, 2000));

start("x11vnc", ["-display", DISPLAY, "-forever", "-nopw", "-rfbport", String(VNC_PORT)]);
await new Promise(r => setTimeout(r, 2000));

start("/opt/noVNC/utils/novnc_proxy", ["--vnc", `localhost:${VNC_PORT}`, "--listen", String(NOVNC_PORT), "--web", "/opt/noVNC"]);
await new Promise(r => setTimeout(r, 3000));

startApi();
console.log(`\n========================================`);
console.log(`VNC BROWSER READY`);
console.log(`Open: http://${process.env.HOST_IP || 'localhost'}:${NOVNC_PORT}/vnc.html`);
console.log(`Capture cookies: curl http://localhost:${API_PORT}/capture?platform=gmail3`);
console.log(`========================================\n`);

try { execSync("pkill -f cloakbrowser/chrom"); } catch(e) {}

console.log("Launching CloakBrowser on display " + DISPLAY);
browser = await launch({ headless: false, args: ["--no-sandbox", "--disable-gpu"] });

ctx = await browser.newContext();
page = await ctx.newPage();

console.log("Navigating to " + defaultUrl);
await page.goto(defaultUrl, { timeout: 30000, waitUntil: "load" });
console.log("Page loaded! Complete login in the VNC window.");
console.log("After logging in, run this to capture cookies:");
console.log(`  curl http://localhost:${API_PORT}/capture?platform=gmail3`);
console.log("Or send SIGUSR1: kill -SIGUSR1 " + process.pid);
console.log("Close terminal to stop.\n");

await new Promise(() => {});
