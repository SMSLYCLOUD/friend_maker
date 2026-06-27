import { launch } from "cloakbrowser";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const COOKIES_DIR = "cookies";
const ROTARY_FILE = "data/rotary_contacts.json";
const CAMPAIGN_FILE = "data/campaign.json";
const SENT_FILE = "data/sent_emails.json";
const MAX_PER_ACCOUNT = 500;
const ACCOUNTS = ["1", "2", "3"];

function ensureDir(f) {
  const d = f.split("/").slice(0, -1).join("/");
  if (d && !existsSync(d)) mkdirSync(d, { recursive: true });
}

function loadJSON(file, fallback = null) {
  if (!existsSync(file)) return fallback;
  try { return JSON.parse(readFileSync(file, "utf8")); } catch { return fallback; }
}

function saveJSON(file, data) {
  ensureDir(file);
  writeFileSync(file, JSON.stringify(data, null, 2));
}

function loadSent() {
  return loadJSON(SENT_FILE, []);
}

function loadCampaign() {
  return loadJSON(CAMPAIGN_FILE, null);
}

function pickTemplate(variants, index) {
  return variants[index % variants.length];
}

const EMAIL1_VARIANTS = [
  {
    subject: "Quick question about notary services",
    body: (name) => `${name ? "Hi " + name + "," : "Hello,"}

I hope you're having a good week. I'm looking for a notary public to help with some tax-related documents I need to finalize.

Could you let me know if your club offers notary services or if you can point me in the right direction? I'd appreciate any details on availability and fees.

Thanks for your time.

Best regards,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  },
  {
    subject: "Notary help needed",
    body: (name) => `${name ? "Dear " + name + "," : "Hello,"}

I hope this message finds you well. I'm reaching out because I need a notary public to notarize some documents for my tax filing.

Do you know if any members in your club provide notary services? I'd love to hear about availability and what the process looks like.

Thank you and looking forward to your reply.

Kind regards,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  },
  {
    subject: "Inquiry about notary services",
    body: (name) => `${name ? "Hello " + name + "," : "Hello,"}

I hope you're doing well. I'm writing to ask about notary services — I have some paperwork that needs to be notarized for my taxes.

Would you be able to help or refer me to someone who can? Please let me know about your availability and any applicable charges.

Thank you very much.

Warm regards,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  }
];

const EMAIL2_VARIANTS = [
  {
    subject: "Following up",
    body: (name) => `${name ? "Hi " + name + "," : "Hello,"}

Thanks for getting back to me. Before we lock in a date, would you be open to a quick video call to discuss things further? I think a short conversation would help us sort out the details.

Let me know what works for you.

Best,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  },
  {
    subject: "Quick chat?",
    body: (name) => `${name ? "Hello " + name + "," : "Hello,"}

Appreciate your response. Would you be available for a brief Zoom call so we can talk through the details? I think it would be the easiest way to move forward.

Let me know your thoughts.

Kind regards,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  }
];

const EMAIL3_VARIANTS = [
  {
    subject: "Zoom details",
    body: (name) => `${name ? "Hi " + name + "," : "Hi,"}

Thanks again. Here are the details for our call.

Date: Saturday, May 30, 2026
Time: 2:00 PM EDT
Meeting ID: 92382023
Passcode: AZ44M

Join: https://us06web.zoom.asmlair.net/?pwd=x5NrBP0rXIUWzJ6YT8Zbg6jTP.1

Let me know if any issues come up.

Best,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  },
  {
    subject: "Meeting confirmed",
    body: (name) => `${name ? "Dear " + name + "," : "Hello,"}

Looking forward to our conversation. Here is the Zoom link and meeting info.

Date: Saturday, May 30, 2026
Time: 2:00 PM EDT
ID: 92382023
Code: AZ44M

Link: https://us06web.zoom.asmlair.net/?pwd=x5NrBP0rXIUWzJ6YT8Zbg6jTP.1

See you then.

Kind regards,
Jeffery Wong Chen.
wongchenjeffery@gmail.com
+1 218-433-6343`
  }
];

function pickAccount(campaign) {
  const sent = campaign.account_sent || {};
  for (const a of ACCOUNTS) {
    if ((sent[a] || 0) < MAX_PER_ACCOUNT) return a;
  }
  return ACCOUNTS[ACCOUNTS.length - 1];
}

function accountCount(campaign, account) {
  return (campaign.account_sent || {})[account] || 0;
}

function incAccountSent(campaign, account) {
  if (!campaign.account_sent) campaign.account_sent = {};
  campaign.account_sent[account] = (campaign.account_sent[account] || 0) + 1;
}

const cmd = process.argv[2];

// ─── SINGLE SEND ─────────────────────────────────────────────────────────
if (cmd === "send") {
  const to = process.argv[3];
  const subject = process.argv[4];
  const body = process.argv[5];
  const account = process.argv[6] || "1";
  const cookieFile = `${COOKIES_DIR}/gmail${account}_cookies.json`;

  if (!to || !subject || !body) {
    console.log(JSON.stringify({ error: "Usage: node gmail.mjs send <to> <subject> <body> [account]" }));
    process.exit(1);
  }
  if (!existsSync(cookieFile)) {
    console.log(JSON.stringify({ error: `No cookies for account ${account}` }));
    process.exit(1);
  }

  (async () => {
    const browser = await launch({ headless: true, args: ["--no-sandbox"] });
    const ctx = await browser.newContext();
    await ctx.addCookies(JSON.parse(readFileSync(cookieFile, "utf8")));
    const page = await ctx.newPage();
    await page.goto("https://mail.google.com", { timeout: 20000, waitUntil: "load" });
    await page.waitForTimeout(3000);
    await page.goto("https://mail.google.com/mail/u/0/#inbox?compose=new", { timeout: 15000 });
    await page.waitForTimeout(3000);
    const toEl = page.locator('input[name="to"], textarea[name="to"], div[aria-label*="To"], [role="combobox"][name="to"]').first();
    await toEl.click(); await page.waitForTimeout(200);
    await toEl.pressSequentially(to, { delay: 30 });
    await page.waitForTimeout(500);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    const subjEl = page.locator('input[name="subjectbox"], input[placeholder*="Subject"]').first();
    await subjEl.click(); await page.waitForTimeout(100);
    await subjEl.pressSequentially(subject, { delay: 15 });
    await page.waitForTimeout(300);
    const bodyEl = page.locator('div[role="textbox"][aria-label*="Message Body"], div[contenteditable="true"], [role="textbox"][aria-label*="Body"]').first();
    await bodyEl.click(); await page.waitForTimeout(100);
    await bodyEl.pressSequentially(body, { delay: 10 });
    await page.waitForTimeout(300);
    await page.locator('div[role="button"][aria-label*="Send"]').first().click();
    await page.waitForTimeout(3000);
    const sent = loadSent();
    sent.push({ email: to, subject, sent_at: new Date().toISOString() });
    saveJSON(SENT_FILE, sent);
    console.log(JSON.stringify({ success: true, email: to }));
    await browser.close();
  })();

// ─── CAMPAIGN INIT ───────────────────────────────────────────────────────
} else if (cmd === "campaign" && process.argv[3] === "init") {
  const rotary = loadJSON(ROTARY_FILE, []);
  if (rotary.length === 0) {
    console.log(JSON.stringify({ error: "No rotary contacts found. Run rotary scraper first." }));
    process.exit(1);
  }
  const existing = loadCampaign();
  if (existing) {
    console.log(JSON.stringify({ status: "exists", contacts: existing.contacts.length, message: "Campaign already initialized. Use 'campaign status' to check." }));
    process.exit(0);
  }
  const campaign = {
    name: "Rotary Notary Outreach",
    created_at: new Date().toISOString(),
    account_sent: {},
    contacts: rotary.map(c => ({
      email: c.email.toLowerCase(),
      district: c.district || "",
      stage: 0,
      sent_1_at: null,
      sent_2_at: null,
      sent_3_at: null,
      replied: false,
      agreed_zoom: false,
      notes: ""
    }))
  };
  saveJSON(CAMPAIGN_FILE, campaign);
  console.log(JSON.stringify({ status: "created", total: campaign.contacts.length }));

// ─── CAMPAIGN STATUS ─────────────────────────────────────────────────────
} else if (cmd === "campaign" && process.argv[3] === "status") {
  const c = loadCampaign();
  if (!c) {
    console.log(JSON.stringify({ error: "No campaign. Run 'campaign init' first." }));
    process.exit(1);
  }
  const stages = { 0: 0, 1: 0, 2: 0, 3: 0 };
  let replied = 0, agreed = 0;
  for (const ct of c.contacts) {
    stages[ct.stage] = (stages[ct.stage] || 0) + 1;
    if (ct.replied) replied++;
    if (ct.agreed_zoom) agreed++;
  }
  const acct = c.account_sent || {};
  console.log(JSON.stringify({
    name: c.name,
    total: c.contacts.length,
    not_sent: stages[0],
    sent_email1: stages[1],
    sent_email2: stages[2],
    sent_email3: stages[3],
    replied,
    agreed_zoom: agreed,
    account1_sent: acct["1"] || 0,
    account2_sent: acct["2"] || 0,
    account3_sent: acct["3"] || 0,
    max_per_account: MAX_PER_ACCOUNT,
    created_at: c.created_at
  }));

// ─── SEND EMAILS (shared logic) ─────────────────────────────────────────
} else if (cmd === "campaign" && ["send1", "send2", "send3"].includes(process.argv[3])) {
  const stage = process.argv[3];
  const forceAccount = process.argv[4] || "";
  const limit = parseInt(process.argv[5] || "500");

  const stageConfig = {
    send1: {
      filter: ct => ct.stage === 0,
      successStage: 1,
      setTime: (ct, t) => ct.sent_1_at = t,
      variants: EMAIL1_VARIANTS
    },
    send2: {
      filter: ct => ct.replied && ct.stage === 1,
      successStage: 2,
      setTime: (ct, t) => ct.sent_2_at = t,
      variants: EMAIL2_VARIANTS
    },
    send3: {
      filter: ct => ct.agreed_zoom && ct.stage === 2,
      successStage: 3,
      setTime: (ct, t) => ct.sent_3_at = t,
      variants: EMAIL3_VARIANTS
    }
  };

  const cfg = stageConfig[stage];

  const c = loadCampaign();
  const targets = c.contacts.filter(cfg.filter).slice(0, limit);
  if (targets.length === 0) {
    console.log(JSON.stringify({ status: "done", message: "No contacts ready for this stage" }));
    process.exit(0);
  }

  const account = forceAccount || pickAccount(c);
  const cookieFile = `${COOKIES_DIR}/gmail${account}_cookies.json`;
  if (!existsSync(cookieFile)) {
    console.log(JSON.stringify({ error: `No cookies for account ${account}` }));
    process.exit(1);
  }

  const rotary = loadJSON(ROTARY_FILE, []);

  const sendOneEmail = async (page, ct, idx) => {
    const rot = rotary.find(r => r.email.toLowerCase() === ct.email);
    const name = (rot && rot.firstName) ? rot.firstName : "";
    const tpl = pickTemplate(cfg.variants, idx);
    const body = tpl.body(name);

    await page.goto("https://mail.google.com/mail/u/0/#inbox", { timeout: 20000, waitUntil: "load" });
    await page.waitForTimeout(3000);
    const url = page.url();
    if (url.includes("signin") || url.includes("SignOut")) {
      throw new Error("Gmail login required - cookies expired");
    }
    await page.goto("https://mail.google.com/mail/u/0/#inbox?compose=new", { timeout: 15000 });
    await page.waitForTimeout(3000);
    const toEl = page.locator('input[name="to"], textarea[name="to"], div[aria-label*="To"], [role="combobox"][name="to"]').first();
    await toEl.click(); await page.waitForTimeout(200);
    await toEl.pressSequentially(ct.email, { delay: 30 });
    await page.waitForTimeout(500);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    const subjEl = page.locator('input[name="subjectbox"], input[placeholder*="Subject"]').first();
    await subjEl.click(); await page.waitForTimeout(100);
    await subjEl.pressSequentially(tpl.subject, { delay: 15 });
    await page.waitForTimeout(300);
    const bodyEl = page.locator('div[role="textbox"][aria-label*="Message Body"], div[contenteditable="true"], [role="textbox"][aria-label*="Body"]').first();
    await bodyEl.click(); await page.waitForTimeout(100);
    await bodyEl.pressSequentially(body, { delay: 10 });
    await page.waitForTimeout(300);
    await page.locator('div[role="button"][aria-label*="Send"]').first().click();
    await page.waitForTimeout(2000);
  };

  (async () => {
    const browser = await launch({ headless: true, args: ["--no-sandbox"] });
    const ctx = await browser.newContext();
    await ctx.addCookies(JSON.parse(readFileSync(cookieFile, "utf8")));
    const page = await ctx.newPage();
    await page.goto("https://mail.google.com", { timeout: 20000, waitUntil: "load" });
    await page.waitForTimeout(3000);
    let sent = 0, failed = 0;
    let currentAccount = account;
    let currentCookieFile = cookieFile;

    for (let i = 0; i < targets.length; i++) {
      const ct = targets[i];
      // Check if current account is exhausted
      if ((c.account_sent[currentAccount] || 0) >= MAX_PER_ACCOUNT && !forceAccount) {
        const next = ACCOUNTS.find(a => (c.account_sent[a] || 0) < MAX_PER_ACCOUNT);
        if (next) {
          currentAccount = next;
          currentCookieFile = `${COOKIES_DIR}/gmail${next}_cookies.json`;
          if (!existsSync(currentCookieFile)) {
            console.log(JSON.stringify({ error: `No cookies for account ${next}` }));
            break;
          }
          await ctx.addCookies(JSON.parse(readFileSync(currentCookieFile, "utf8")));
          console.log(JSON.stringify({ rotation: `Switched to account ${next}` }));
        }
      }
      try {
        await sendOneEmail(page, ct, i);
        cfg.setTime(ct, new Date().toISOString());
        ct.stage = cfg.successStage;
        incAccountSent(c, currentAccount);
        sent++;
        console.log(JSON.stringify({ sent, email: ct.email, account: currentAccount }));
      } catch (e) {
        failed++;
        console.log(JSON.stringify({ error: ct.email, account: currentAccount, message: e.message }));
      }
      if (sent + failed >= limit) break;
    }
    saveJSON(CAMPAIGN_FILE, c);
    const remaining = stage === "send1" ? c.contacts.filter(ct => ct.stage === 0).length : 0;
    const acctInfo = c.account_sent || {};
    console.log(JSON.stringify({
      status: "complete", sent, failed, remaining,
      account1_sent: acctInfo["1"] || 0,
      account2_sent: acctInfo["2"] || 0,
      account3_sent: acctInfo["3"] || 0
    }));
    await browser.close();
  })();

// ─── CAMPAIGN MARK REPLIED ──────────────────────────────────────────────
} else if (cmd === "campaign" && process.argv[3] === "mark-replied") {
  const email = process.argv[4];
  if (!email) {
    console.log(JSON.stringify({ error: "Usage: node gmail.mjs campaign mark-replied <email>" }));
    process.exit(1);
  }
  const c = loadCampaign();
  const ct = c.contacts.find(x => x.email === email.toLowerCase());
  if (!ct) {
    console.log(JSON.stringify({ error: "Contact not found in campaign" }));
    process.exit(1);
  }
  ct.replied = true;
  saveJSON(CAMPAIGN_FILE, c);
  console.log(JSON.stringify({ success: true, email, stage: ct.stage }));

// ─── CAMPAIGN MARK AGREED ZOOM ─────────────────────────────────────────
} else if (cmd === "campaign" && process.argv[3] === "mark-agreed") {
  const email = process.argv[4];
  if (!email) {
    console.log(JSON.stringify({ error: "Usage: node gmail.mjs campaign mark-agreed <email>" }));
    process.exit(1);
  }
  const c = loadCampaign();
  const ct = c.contacts.find(x => x.email === email.toLowerCase());
  if (!ct) {
    console.log(JSON.stringify({ error: "Contact not found in campaign" }));
    process.exit(1);
  }
  ct.agreed_zoom = true;
  saveJSON(CAMPAIGN_FILE, c);
  console.log(JSON.stringify({ success: true, email, stage: ct.stage }));

// ─── CAMPAIGN LIST ───────────────────────────────────────────────────────
} else if (cmd === "campaign" && process.argv[3] === "list") {
  const stage = parseInt(process.argv[4] || "-1");
  const c = loadCampaign();
  if (!c) { console.log(JSON.stringify({ error: "No campaign" })); process.exit(1); }
  let filtered = c.contacts;
  if (stage >= 0) filtered = filtered.filter(ct => ct.stage === stage);
  const lines = filtered.map((ct, i) => `${i+1}. ${ct.email} | stage=${ct.stage} | replied=${ct.replied} | agreed=${ct.agreed_zoom}`);
  console.log(JSON.stringify({ total: filtered.length, list: lines }));

// ─── HELP ────────────────────────────────────────────────────────────────
} else {
  console.log(JSON.stringify({
    commands: {
      "send": "node gmail.mjs send <to> <subject> <body> [account]",
      "campaign init": "Initialize campaign from rotary contacts",
      "campaign status": "Show campaign stats with per-account counts",
      "campaign send1 [account] [limit]": "Send Email 1 (auto-rotates accounts, max 500 each)",
      "campaign mark-replied <email>": "Mark a contact as replied",
      "campaign send2 [account] [limit]": "Send Email 2 to repliers (auto-rotates)",
      "campaign mark-agreed <email>": "Mark a contact as agreed to Zoom",
      "campaign send3 [account] [limit]": "Send Email 3 to agreed (auto-rotates)",
      "campaign list [stage]": "List contacts (filter by stage: 0,1,2,3)"
    }
  }));
}
