import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
chromium.use(StealthPlugin());
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const BASE = "https://substack.com";
const COOKIE_PATH = "cookies/substack_cookies.json";
const ACTIONS = ["login", "search", "follow", "unfollow"];

function ensureDir() {
  const dir = COOKIE_PATH.split("/").slice(0, -1).join("/");
  if (dir && !existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function randomDelay(ms) {
  return new Promise(r => setTimeout(r, ms + Math.random() * 1000));
}

async function loadOrLogin(ctx, page, user, pass) {
  if (existsSync(COOKIE_PATH)) {
    const cookies = JSON.parse(readFileSync(COOKIE_PATH, "utf-8"));
    await ctx.addCookies(cookies);
    await page.goto(BASE, { timeout: 30000 });
    await page.waitForTimeout(3000);
    if (await page.locator("a[href*='/dashboard'], [data-testid='user-menu'], div.user-menu-button").count() > 0) return true;
  }
  if (!user || !pass) return false;
  await page.goto(BASE + "/sign-in", { timeout: 30000 });
  await page.waitForTimeout(2000);
  await page.fill('input[type="email"], input[name="email"]', user);
  await randomDelay(400);
  await page.click('button:has-text("Continue"), button[type="submit"]');
  await page.waitForTimeout(2000);
  await page.fill('input[type="password"], input[name="password"]', pass);
  await randomDelay(400);
  await page.click('button[type="submit"]:has-text("Sign in")');
  await page.waitForTimeout(5000);
  const ok = await page.locator("a[href*='/dashboard'], [data-testid='user-menu'], div.user-menu-button").count() > 0;
  if (ok) {
    ensureDir();
    writeFileSync(COOKIE_PATH, JSON.stringify(await ctx.cookies(), null, 2));
  }
  return ok;
}

async function main() {
  const action = process.argv[2];
  if (!action || !ACTIONS.includes(action)) {
    console.log(JSON.stringify({ error: "Usage: node substack.mjs <login|search|follow|unfollow> [args...]" }));
    return;
  }
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  let result;

  try {
    if (action !== "login" && action !== "search") {
      const [user, pass] = [process.env.SUBSTACK_USER, process.env.SUBSTACK_PASS];
      if (!await loadOrLogin(ctx, page, user, pass)) {
        result = { success: false, error: "Not logged in. Run 'login' first or set SUBSTACK_USER/SUBSTACK_PASS env vars" };
        console.log(JSON.stringify(result));
        return;
      }
    }

    switch (action) {
      case "login": {
        const [u, p] = [process.argv[3] || process.env.SUBSTACK_USER, process.argv[4] || process.env.SUBSTACK_PASS];
        if (!u || !p) { result = { error: "Email and password required" }; break; }
        const ok = await loadOrLogin(ctx, page, u, p);
        result = ok ? { success: true, note: "Cookies saved" } : { success: false, error: "Login failed" };
        break;
      }
      case "search": {
        const query = process.argv[3];
        await page.goto(BASE + "/search/" + encodeURIComponent(query) + "?focused=users", { timeout: 30000 });
        await page.waitForTimeout(4000);
        const userLinks = await page.locator("a[href*='/@']").all();
        const seen = new Set();
        const users = [];
        for (const link of userLinks) {
          const href = await link.getAttribute("href").catch(() => "");
          if (!href || seen.has(href)) continue;
          seen.add(href);
          const text = (await link.innerText().catch(() => "")).trim();
          if (text && text.length > 2 && !text.includes("utm_source")) {
            const lines = text.split("\n").filter(Boolean);
            users.push({ name: lines[0] || "", handle: lines[1] || "", description: lines.slice(2).join(" ").substring(0, 100) });
            if (users.length >= 15) break;
          }
        }
        result = users.length > 0 ? { count: users.length, users } : { message: "No users found" };
        break;
      }
      case "follow": {
        const handle = process.argv[3].replace("@", "");
        await page.goto(BASE + "/@" + handle, { timeout: 30000 });
        await page.waitForTimeout(3000);
        const btn = page.locator("button:has-text('Follow'), button:has-text('Subscribe'), [aria-label*='Follow']").first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          await btn.click();
          await page.waitForTimeout(2000);
          result = { success: true };
        } else {
          result = { success: false, error: "Already following or button not found" };
        }
        break;
      }
      case "unfollow": {
        const handle = process.argv[3].replace("@", "");
        await page.goto(BASE + "/@" + handle, { timeout: 30000 });
        await page.waitForTimeout(3000);
        const btn = page.locator("button:has-text('Following'), [aria-label*='Unfollow'], button:has-text('Unsubscribe')").first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          await btn.click();
          await page.waitForTimeout(1000);
          const confirm = page.locator("button:has-text('Unfollow'), button:has-text('Confirm')").first();
          if (await confirm.count() > 0) await confirm.click();
          await page.waitForTimeout(2000);
          result = { success: true };
        } else {
          result = { success: false, error: "Not following or button not found" };
        }
        break;
      }
    }
  } catch (e) { result = { error: e.message }; }
  finally { await browser.close(); }

  console.log(JSON.stringify(result));
}

main();
