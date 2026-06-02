import { chromium } from "playwright-core";

const BASE = "https://www.notarycafe.com";

async function main() {
  const action = process.argv[2];
  if (!action) { console.log(JSON.stringify({ error: "Usage: node nc.mjs <action> [args...]" })); return; }

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  let result;

  try {
    switch (action) {
      case "register": {
        const [firstName, lastName, email, pass, workPhone, street, city, state, zip] = process.argv.slice(3, 12);
        await page.goto(BASE + "/register", { timeout: 30000 });
        await page.waitForTimeout(3000);
        // Click "Switch to Free Account" if visible to hide CC fields
        const freeBtn = page.locator('button:has-text("Switch to Free Account")');
        if (await freeBtn.count() > 0) {
          await freeBtn.click();
          await page.waitForTimeout(1000);
        }
        const fields = {
          'input[placeholder="First Name"]:not([id])': firstName || "",
          'input[placeholder="Last Name"]:not([id])': lastName || "",
          'input[placeholder="Email"]:not([id])': email || "",
          'input[placeholder="Password"]:not([id])': pass || "",
          'input[placeholder="Confirm Password"]:not([id])': pass || "",
          'input[placeholder="Work Number"]:not([id])': workPhone || "",
          'input[placeholder="Street Adress"]:not([id])': street || "",
          'input[placeholder="City"]:not([id])': city || "",
          'input[placeholder="Zip"]:not([id])': zip || "",
        };
        for (const [sel, val] of Object.entries(fields)) {
          const el = page.locator(sel).first();
          if (await el.count() > 0 && val) await el.fill(val);
        }
        if (state) {
          const stateNames = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"};
          const fullName = stateNames[state.toUpperCase()] || state;
          await page.locator("select").first().selectOption(fullName);
          await page.waitForTimeout(500);
        }
        await page.locator('button:has-text("Register")').first().click();
        await page.waitForTimeout(5000);
        const currentUrl = page.url();
        const bodyText = await page.locator("body").innerText();
        const hasError = bodyText.includes("error") || bodyText.includes("Error") || bodyText.includes("required");
        result = {
          success: currentUrl !== BASE + "/register" && !hasError,
          url: currentUrl,
          message: hasError ? bodyText.substring(0, 500) : "Registration submitted",
        };
        break;
      }
      case "login": {
        const [email, pass] = [process.argv[3], process.argv[4]];
        await page.goto(BASE + "/account/logon", { timeout: 30000 });
        await page.waitForTimeout(2000);
        await page.fill('input[name="UserName"]', email);
        await page.fill('input[name="Password"]', pass);
        await page.locator('button:has-text("Log In"), input[type="submit"]').first().click();
        await page.waitForTimeout(3000);
        result = { success: page.url() !== BASE + "/account/logon", url: page.url() };
        break;
      }
      case "search": {
        const loc = process.argv[3];
        await page.goto(BASE + "/find-a-notary", { timeout: 30000 });
        await page.waitForTimeout(2000);
const box = page.locator('#SearchString');
      await box.waitFor({ timeout: 5000 });
      await box.fill(loc);
      await box.press("Enter");
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
      result = results.length > 0 ? { count: results.length, results } : { message: "No results found" };
        break;
      }
      case "profile": {
        const url = process.argv[3];
        await page.goto(url.startsWith("http") ? url : BASE + url, { timeout: 30000 });
        await page.waitForTimeout(2000);
        const name = await page.locator('[class*="name"], h1, h2').first().textContent() || "";
        const loc2 = await page.locator('[class*="location"], [class*="city"]').first().textContent() || "";
        const about = await page.locator('[class*="about"], [class*="bio"]').first().textContent() || "";
        result = { name: name.trim(), location: loc2.trim(), about: about.trim(), url: page.url() };
        break;
      }
      case "message": {
        const [profileUrl, ...msgParts] = process.argv.slice(3);
        const message = msgParts.join(" ");
        await page.goto(profileUrl.startsWith("http") ? profileUrl : BASE + profileUrl, { timeout: 30000 });
        await page.waitForTimeout(2000);
        const msgBtn = page.locator('a[href*="message"], button:has-text("Message")').first();
        if (await msgBtn.count() > 0) { await msgBtn.click(); await page.waitForTimeout(2000); }
        const ta = page.locator("textarea, [contenteditable='true']").first();
        if (await ta.count() > 0) {
          await ta.fill(message);
          await page.locator('button[type="submit"], button:has-text("Send")').first().click();
          await page.waitForTimeout(2000);
          result = { success: true };
        } else result = { success: false, error: "Message form not found" };
        break;
      }
      default:
        result = { error: "Unknown action: " + action + ". Valid: login, search, profile, message" };
    }
  } catch (e) { result = { error: e.message }; }
  finally { await browser.close(); }

  console.log(JSON.stringify(result));
}

main();
