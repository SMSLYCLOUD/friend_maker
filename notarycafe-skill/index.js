import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { chromium } from "playwright-core";

const BASE = "https://www.notarycafe.com";

let _browser = null;
let _loggedInUser = null;

async function getBrowser() {
  if (!_browser || !_browser.isConnected()) {
    _browser = await chromium.launch({ headless: true });
  }
  return _browser;
}

async function ncLogin(page, email, password) {
  await page.goto(BASE + "/login", { timeout: 30000 });
  await page.waitForTimeout(2000);
  await page.locator('input[name="email"], input[type="email"]').fill(email);
  await page.locator('input[name="password"], input[type="password"]').fill(password);
  await page.locator('button[type="submit"], input[type="submit"]').click();
  await page.waitForTimeout(3000);
  const url = page.url();
  return url.includes("dashboard") || url.includes("profile") || url.includes("home") || url === BASE + "/";
}

async function searchNotaries(page, zipOrCity) {
  await page.goto(BASE + "/find-a-notary", { timeout: 30000 });
  await page.waitForTimeout(2000);
  const searchBox = page.locator('#SearchString');
  await searchBox.waitFor({ timeout: 5000 });
  await searchBox.fill(zipOrCity);
  await searchBox.press("Enter");
  await page.waitForTimeout(4000);
  const body = await page.locator("body").innerText();
  const lines = body.split("\n").map(l => l.trim()).filter(Boolean);
  const results = [];
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] === "View Profile") {
      const email = i > 5 ? lines[i - 5] : "";
      const phone = i > 6 ? lines[i - 6] : "";
      const zip = i > 7 ? lines[i - 7] : "";
      const loc = i > 8 ? lines[i - 8] : "";
      const company = i > 9 ? lines[i - 9] : "";
      const name = i > 10 ? lines[i - 10] : lines[i - 1];
      if (name && !name.includes("Profile") && !name.includes("Completion") && name.length > 2) {
        results.push({ name, location: loc, phone, email, company });
        if (results.length >= 20) break;
      }
    }
  }
  return results.length > 0 ? { count: results.length, results } : { message: "No results found" };
}

async function scrapeProfile(page, profileUrl) {
  await page.goto(profileUrl.startsWith("http") ? profileUrl : BASE + profileUrl, { timeout: 30000 });
  await page.waitForTimeout(2000);
  const name = await page.locator('[class*="name"], h1, h2').first().textContent().catch(() => "");
  const loc = await page.locator('[class*="location"], [class*="city"]').first().textContent().catch(() => "");
  const about = await page.locator('[class*="about"], [class*="bio"], [class*="description"]').first().textContent().catch(() => "");
  const contact = await page.locator('[class*="contact"], [class*="email"], [class*="phone"]').first().textContent().catch(() => "");
  return {
    name: name?.trim(),
    location: loc?.trim(),
    about: about?.trim(),
    contact: contact?.trim(),
    url: page.url(),
  };
}

async function sendMessage(page, profileUrl, message) {
  await page.goto(profileUrl.startsWith("http") ? profileUrl : BASE + profileUrl, { timeout: 30000 });
  await page.waitForTimeout(2000);
  const msgBtn = page.locator('a[href*="message"], button:has-text("Message"), a:has-text("Contact")').first();
  if (await msgBtn.count() > 0) {
    await msgBtn.click();
    await page.waitForTimeout(2000);
  }
  const textarea = page.locator('textarea, [contenteditable="true"], [role="textbox"]').first();
  if (await textarea.count() > 0) {
    await textarea.fill(message);
    await page.locator('button[type="submit"], button:has-text("Send"), input[type="submit"]').first().click();
    await page.waitForTimeout(2000);
    return { success: true };
  }
  return { success: false, error: "Message form not found" };
}

async function viewMyProfile(page) {
  await page.goto(BASE + "/profile", { timeout: 30000 });
  await page.waitForTimeout(2000);
  const text = await page.locator("body").textContent().catch(() => "");
  return { profile: text?.substring(0, 2000) };
}

export default definePluginEntry({
  id: "notarycafe-agent",
  name: "NotaryCafe Agent",
  description: "NotaryCafe.com automation: login, search notaries, scrape profiles, send messages",
  register(api) {
    api.registerTool({
      name: "nc_login",
      description: "Log into NotaryCafe.com with email and password.",
      params: {
        type: "object",
        properties: {
          email: { type: "string" },
          password: { type: "string" },
        },
        required: ["email", "password"],
      },
      handler: async ({ email, password }) => {
        const b = await getBrowser();
        const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
        const page = await ctx.newPage();
        const ok = await ncLogin(page, email, password);
        if (ok) {
          _loggedInUser = email;
          return { success: true, url: page.url() };
        }
        await ctx.close();
        return { success: false, error: "Login failed", url: page.url() };
      },
    });

    api.registerTool({
      name: "nc_search",
      description: "Search for notaries by zip code or city.",
      params: {
        type: "object",
        properties: {
          location: { type: "string", description: "Zip code or city name" },
        },
        required: ["location"],
      },
      handler: async ({ location }) => {
        const b = await getBrowser();
        const ctx = b.contexts()[0] || await b.newContext();
        const page = ctx.pages()[0] || await ctx.newPage();
        return await searchNotaries(page, location);
      },
    });

    api.registerTool({
      name: "nc_scrape_profile",
      description: "View a notary's profile details.",
      params: {
        type: "object",
        properties: {
          url: { type: "string", description: "Full URL or path to the profile" },
        },
        required: ["url"],
      },
      handler: async ({ url }) => {
        const b = await getBrowser();
        const ctx = b.contexts()[0] || await b.newContext();
        const page = ctx.pages()[0] || await ctx.newPage();
        return await scrapeProfile(page, url);
      },
    });

    api.registerTool({
      name: "nc_send_message",
      description: "Send a message to a notary via their profile.",
      params: {
        type: "object",
        properties: {
          url: { type: "string" },
          message: { type: "string" },
        },
        required: ["url", "message"],
      },
      handler: async ({ url, message }) => {
        const b = await getBrowser();
        const ctx = b.contexts()[0] || await b.newContext();
        const page = ctx.pages()[0] || await ctx.newPage();
        return await sendMessage(page, url, message);
      },
    });
  },
});
