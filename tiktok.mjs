import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
chromium.use(StealthPlugin());
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const BASE = "https://www.tiktok.com";
const COOKIE_PATH = "cookies/tiktok_cookies.json";
const ACTIONS = ["login", "search", "follow", "unfollow", "dm", "like"];

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
    await page.waitForTimeout(4000);
    if (await page.locator('[data-testid="user-avatar"], .tiktok-avatar, a[href*="/@"]').count() > 0) return true;
  }
  if (!user || !pass) return false;
  await page.goto(BASE + "/login/phone-or-email/email", { timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.fill('input[name="username"]', user);
  await randomDelay(500);
  await page.fill('input[type="password"]', pass);
  await randomDelay(500);
  await page.click('button:has-text("Log in")');
  await page.waitForTimeout(10000);
  const ok = await page.locator('[data-testid="user-avatar"], .tiktok-avatar, a[href*="/@"]').count() > 0;
  if (ok) {
    ensureDir();
    writeFileSync(COOKIE_PATH, JSON.stringify(await ctx.cookies(), null, 2));
  }
  return ok;
}

async function main() {
  const action = process.argv[2];
  if (!action || !ACTIONS.includes(action)) {
    console.log(JSON.stringify({ error: "Usage: node tiktok.mjs <login|search|follow|unfollow|dm|like> [args...]" }));
    return;
  }
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  let result;

  try {
    if (action !== "login") {
      const [user, pass] = [process.env.TIKTOK_USER, process.env.TIKTOK_PASS];
      if (!await loadOrLogin(ctx, page, user, pass)) {
        result = { success: false, error: "Not logged in. Run 'login' first or set TIKTOK_USER/TIKTOK_PASS env vars" };
        console.log(JSON.stringify(result));
        return;
      }
    }

    switch (action) {
      case "login": {
        const [u, p] = [process.argv[3] || process.env.TIKTOK_USER, process.argv[4] || process.env.TIKTOK_PASS];
        if (!u || !p) { result = { error: "Email and password required" }; break; }
        const ok = await loadOrLogin(ctx, page, u, p);
        result = ok ? { success: true, note: "Cookies saved" } : { success: false, error: "Login failed" };
        break;
      }
      case "search": {
        const query = process.argv[3];
        await page.goto(BASE + "/search/user?q=" + encodeURIComponent(query), { timeout: 30000 });
        await page.waitForTimeout(4000);
        const userLinks = await page.locator('a[href*="/@"], div[data-testid*="user"] a').all();
        const seen = new Set();
        const users = [];
        for (const link of userLinks) {
          const href = await link.getAttribute("href").catch(() => "");
          if (!href || !href.includes("/@") || seen.has(href)) continue;
          seen.add(href);
          const text = (await link.innerText().catch(() => "")).trim().substring(0, 100);
          if (text) {
            users.push({ handle: href.split("/@").pop(), text });
            if (users.length >= 10) break;
          }
        }
        result = users.length > 0 ? { count: users.length, users } : { message: "No users found" };
        break;
      }
      case "follow": {
        const handle = process.argv[3].replace("@", "");
        await page.goto(BASE + "/@" + handle, { timeout: 30000 });
        await page.waitForTimeout(3000);
        const btn = page.locator('button:has-text("Follow")').first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          await btn.click();
          await randomDelay(1000);
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
        const btn = page.locator('button:has-text("Following")').first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          await btn.click();
          await page.waitForTimeout(1000);
          const confirm = page.locator('button:has-text("Unfollow")').first();
          if (await confirm.count() > 0) await confirm.click();
          await randomDelay(1000);
          result = { success: true };
        } else {
          result = { success: false, error: "Not following or button not found" };
        }
        break;
      }
      case "dm": {
        const [target, msg] = [process.argv[3].replace("@", ""), process.argv.slice(4).join(" ")];
        await page.goto(BASE + "/@" + target, { timeout: 30000 });
        await page.waitForTimeout(3000);
        const msgBtn = page.locator('button:has-text("Message")').first();
        if (await msgBtn.count() > 0 && await msgBtn.isVisible()) {
          await msgBtn.click();
          await page.waitForTimeout(2000);
          const box = page.locator('div[contenteditable="true"], textarea, [role="textbox"]').first();
          if (await box.count() > 0) {
            await box.fill(msg);
            await box.press("Enter");
            result = { success: true };
          } else result = { success: false, error: "Message input not found" };
        } else {
          result = { success: false, error: "Message button not available" };
        }
        break;
      }
      case "like": {
        const handle = process.argv[3].replace("@", "");
        await page.goto(BASE + "/@" + handle, { timeout: 30000 });
        await page.waitForTimeout(3000);
        const likeBtn = page.locator('button[data-testid*="like"]').first();
        if (await likeBtn.count() > 0 && await likeBtn.isVisible()) {
          await likeBtn.click();
          result = { success: true };
        } else {
          result = { success: false, error: "Like button not found" };
        }
        break;
      }
    }
  } catch (e) { result = { success: false, error: e.message }; }
  finally { await browser.close(); }

  console.log(JSON.stringify(result));
}

main();
