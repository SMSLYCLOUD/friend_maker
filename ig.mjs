import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
chromium.use(StealthPlugin());
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const BASE = "https://www.instagram.com";
const COOKIE_PATH = "cookies/ig_cookies.json";
const ACTIONS = ["login", "follow", "unfollow", "dm", "search"];

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
    await page.goto(BASE + "/", { timeout: 30000 });
    await page.waitForTimeout(3000);
    if (await page.locator('svg[aria-label="New post"], svg[aria-label="Home"]').count() > 0) return true;
  }
  if (!user || !pass) return false;
  await page.goto(BASE, { timeout: 30000, waitUntil: "load" });
  await page.waitForTimeout(3000);
  // Stealth mode: login form appears directly; classic mode: click "Log in" first
  const loginBtn = page.locator('button:has-text("Log in")');
  if (await loginBtn.count() > 0) {
    await loginBtn.click();
    await page.waitForTimeout(2000);
  }
  await page.fill('input[name="email"]', user);
  await randomDelay(500);
  await page.fill('input[name="pass"]', pass);
  await randomDelay(500);
  await page.press('input[name="pass"]', 'Enter');
  await page.waitForTimeout(8000);
  const ok = await page.locator('svg[aria-label="New post"], svg[aria-label="Home"]').count() > 0;
  if (ok) {
    ensureDir();
    writeFileSync(COOKIE_PATH, JSON.stringify(await ctx.cookies(), null, 2));
  }
  return ok;
}

async function main() {
  const action = process.argv[2];
  if (!action || !ACTIONS.includes(action)) {
    console.log(JSON.stringify({ error: "Usage: node ig.mjs <login|follow|unfollow|dm|search> [args...]" }));
    return;
  }
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  let result;

  try {
    if (action !== "login") {
      const [user, pass] = [process.env.IG_USER, process.env.IG_PASS];
      if (!await loadOrLogin(ctx, page, user, pass)) {
        result = { success: false, error: "Not logged in. Run 'login' first or set IG_USER/IG_PASS env vars" };
        console.log(JSON.stringify(result));
        return;
      }
    }

    switch (action) {
      case "login": {
        const [u, p] = [process.argv[3] || process.env.IG_USER, process.argv[4] || process.env.IG_PASS];
        if (!u || !p) { result = { error: "Username and password required" }; break; }
        const ok = await loadOrLogin(ctx, page, u, p);
        result = ok ? { success: true, note: "Cookies saved" } : { success: false, error: "Login failed" };
        break;
      }
      case "follow": {
        const target = process.argv[3];
        await page.goto(BASE + "/" + target + "/", { timeout: 20000 });
        await page.waitForTimeout(2000);
        const btn = page.locator('button:has-text("Follow")');
        if (await btn.count() > 0) { await btn.click(); await randomDelay(500); result = { success: true }; }
        else result = { success: false, error: "Already following or button not found" };
        break;
      }
      case "unfollow": {
        const target = process.argv[3];
        await page.goto(BASE + "/" + target + "/", { timeout: 20000 });
        await page.waitForTimeout(2000);
        const following = page.locator('button:has-text("Following")');
        if (await following.count() > 0) {
          await following.click(); await page.waitForTimeout(500);
          await page.locator('button:has-text("Unfollow")').click();
          await page.waitForTimeout(500);
          result = { success: true };
        } else result = { success: false, error: "Not following" };
        break;
      }
      case "dm": {
        const [target, msg] = [process.argv[3], process.argv.slice(4).join(" ")];
        await page.goto(BASE + "/" + target + "/", { timeout: 20000 });
        await page.waitForTimeout(2000);
        const msgBtn = page.locator('button:has-text("Message")');
        if (await msgBtn.count() > 0) {
          await msgBtn.click(); await page.waitForTimeout(1500);
          const box = page.locator('div[contenteditable="true"][role="textbox"]');
          await box.fill(msg); await box.press("Enter");
          result = { success: true };
        } else result = { success: false, error: "Message button not available" };
        break;
      }
      case "search": {
        const query = process.argv[3];
        await page.goto(BASE + "/explore/search/?query=" + encodeURIComponent(query), { timeout: 20000 });
        await page.waitForTimeout(3000);
        const links = await page.locator("a[href^='/']").all();
        const seen = new Set();
        const users = [];
        for (const link of links) {
          const href = await link.getAttribute("href").catch(() => "");
          if (!href || !href.match(/^\/([^/]+)\/$/) || seen.has(href)) continue;
          seen.add(href);
          const text = (await link.innerText().catch(() => "")).trim();
          if (text && text.length > 1) {
            users.push({ handle: href.replace(/\//g, ""), name: text });
            if (users.length >= 10) break;
          }
        }
        result = users.length > 0 ? { count: users.length, users } : { message: "No users found" };
        break;
      }
    }
  } catch (e) { result = { success: false, error: e.message }; }
  finally { await browser.close(); }

  console.log(JSON.stringify(result));
}

main();
