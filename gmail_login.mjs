import { launch } from "cloakbrowser";
import { writeFileSync, existsSync, mkdirSync } from "fs";

const email = process.argv[2];
const password = process.argv[3];
const accountNum = process.argv[4] || "1";
const cookieFile = `cookies/gmail${accountNum}_cookies.json`;

if (!email || !password) {
  console.log(JSON.stringify({ error: "Usage: node gmail_login.mjs <email> <password> [account_num]" }));
  process.exit(1);
}

function ensureDir() {
  const dir = cookieFile.split("/").slice(0, -1).join("/");
  if (dir && !existsSync(dir)) mkdirSync(dir, { recursive: true });
}

(async () => {
  const browser = await launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  try {
    // Check if cookies already exist
    if (existsSync(cookieFile)) {
      const cookies = JSON.parse(require("fs").readFileSync(cookieFile, "utf-8"));
      await ctx.addCookies(cookies);
      await page.goto("https://mail.google.com", { timeout: 15000 });
      await page.waitForTimeout(2000);
      if (page.url().includes("mail")) {
        console.log(JSON.stringify({ success: true, note: "Already logged in via cookies" }));
        await browser.close();
        return;
      }
    }

    await page.goto("https://accounts.google.com/signin", { timeout: 30000, waitUntil: "load" });
    await page.waitForTimeout(2000);
    await page.fill('input[type="email"]', email);
    await new Promise(r => setTimeout(r, 500 + Math.random() * 500));
    await page.click("#identifierNext");
    await page.waitForTimeout(3000);
    const pwInput = page.locator('input[type="password"]');
    if (await pwInput.count() === 0) {
      const body = await page.evaluate(() => document.body.innerText);
      console.log(JSON.stringify({ success: false, error: "No password field", body: body.substring(0, 500) }));
      await browser.close();
      return;
    }
    await pwInput.fill(password);
    await new Promise(r => setTimeout(r, 500 + Math.random() * 500));
    await page.click("#passwordNext");
    await page.waitForTimeout(8000);
    const url = page.url();
    const ok = url.includes("myaccount") || url.includes("mail.google") || !url.includes("signin");
    if (ok) {
      ensureDir();
      writeFileSync(cookieFile, JSON.stringify(await ctx.cookies(), null, 2));
      console.log(JSON.stringify({ success: true, note: "Gmail login successful, cookies saved", file: cookieFile }));
    } else {
      const body = await page.evaluate(() => document.body.innerText);
      const err = body.split("\n").find(l => l.toLowerCase().includes("wrong") || l.toLowerCase().includes("couldn't") || l.toLowerCase().includes("incorrect"));
      console.log(JSON.stringify({ success: false, error: err || "Login failed", url }));
    }
  } catch (e) {
    console.log(JSON.stringify({ success: false, error: e.message }));
  }
  await browser.close();
})();
