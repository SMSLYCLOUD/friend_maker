import { definePluginEntry } from "openclaw";

const IG_URLS = {
  login: "https://www.instagram.com/accounts/login/",
  home: "https://www.instagram.com/",
  followers: (u: string) => `https://www.instagram.com/${u}/followers/`,
  profile: (u: string) => `https://www.instagram.com/${u}/`,
};

async function login(page: any, username: string, password: string, cookies?: string): Promise<boolean> {
  if (cookies) {
    try {
      const parsed = JSON.parse(cookies);
      await page.context.add_cookies(parsed);
      await page.goto(IG_URLS.home);
      await page.wait_for_timeout(3000);
      if (await page.locator('svg[aria-label="New post"]').count() > 0) return true;
    } catch {}
  }
  await page.goto(IG_URLS.login, { timeout: 30000 });
  await page.wait_for_timeout(3000);
  const u = page.locator('input[name="username"]');
  await u.waitFor({ timeout: 10000 });
  await u.fill(username);
  await page.wait_for_timeout(500);
  const next = page.locator('button:has-text("Next")');
  if (await next.count() > 0) { await next.click(); await page.wait_for_timeout(1000); }
  const p = page.locator('input[name="password"]');
  await p.fill(password);
  await page.locator('button[type="submit"]').click();
  await page.wait_for_timeout(5000);
  try {
    await page.wait_for_selector('svg[aria-label="New post"]', { timeout: 15000 });
    return true;
  } catch { return false; }
}

async function doFollow(page: any, target: string) {
  await page.goto(IG_URLS.profile(target), { timeout: 20000 });
  await page.wait_for_timeout(2000);
  if (await page.locator('button:has-text("Following")').count() > 0) return { success: true };
  const btn = page.locator('button:has-text("Follow")');
  if (await btn.count() > 0) { await btn.click(); await page.wait_for_timeout(1000); return { success: true }; }
  return { success: false, error: "Follow button not found" };
}

async function doUnfollow(page: any, target: string) {
  await page.goto(IG_URLS.profile(target), { timeout: 20000 });
  await page.wait_for_timeout(2000);
  const btn = page.locator('button:has-text("Following")');
  if (await btn.count() > 0) {
    await btn.click(); await page.wait_for_timeout(500);
    const confirm = page.locator('button:has-text("Unfollow")');
    if (await confirm.count() > 0) { await confirm.click(); await page.wait_for_timeout(1000); return { success: true }; }
  }
  return { success: false, error: "Not following" };
}

async function doSendDM(page: any, target: string, message: string) {
  await page.goto(IG_URLS.profile(target), { timeout: 20000 });
  await page.wait_for_timeout(2000);
  const msgBtn = page.locator('button:has-text("Message")');
  if (await msgBtn.count() > 0) {
    await msgBtn.click(); await page.wait_for_timeout(1500);
    const box = page.locator('div[contenteditable="true"][role="textbox"]');
    await box.waitFor({ timeout: 5000 });
    await box.fill(message);
    await box.press("Enter");
    await page.wait_for_timeout(1000);
    return { success: true };
  }
  return { success: false, error: "Message button not found" };
}

async function scrapeFollowers(page: any, target: string, count: number = 100): Promise<string[]> {
  await page.goto(IG_URLS.followers(target), { timeout: 20000 });
  await page.wait_for_timeout(2000);
  const scraped: string[] = [];
  for (let i = 0; i < count / 10 && scraped.length < count; i++) {
    await page.evaluate(() => window.scrollBy(0, 500));
    await page.wait_for_timeout(800);
    const links = await page.locator('a[href*="/"]').all();
    for (const link of links) {
      const href = await link.getAttribute("href");
      const u = href?.replace("/", "").replace(/\/$/, "").split("?")[0];
      if (u && u !== target && !scraped.includes(u)) scraped.push(u);
      if (scraped.length >= count) break;
    }
  }
  return scraped;
}

async function runBombing(page: any, targets: string[], action: string, message: string, count: number) {
  let succeeded = 0; const failed: string[] = [];
  for (const target of targets.slice(0, count)) {
    try {
      const result = action === "follow" ? await doFollow(page, target) : await doSendDM(page, target, message);
      if (result.success) succeeded++; else failed.push(`${target}: ${result.error}`);
      await page.wait_for_timeout(3000 + Math.random() * 4000);
    } catch (e) { failed.push(`${target}: ${e}`); }
  }
  return { processed: targets.length, succeeded, failed, summary: `${succeeded}/${targets.length} ${action} actions succeeded` };
}

export default definePluginEntry({
  id: "ig-agent",
  name: "IG Agent",
  description: "Instagram automation: login, follow, unfollow, DM, scrape followers, bombing campaigns",
  register(api) {
    api.registerTool({
      name: "ig_login",
      description: "Log into an Instagram account. Returns session cookies on success.",
      params: {
        type: "object",
        properties: {
          username: { type: "string", description: "Instagram username or email" },
          password: { type: "string", description: "Instagram password" },
          sessionCookies: { type: "string", description: "Optional JSON cookies for fast restore" },
        },
        required: ["username", "password"],
      },
      handler: async ({ username, password, sessionCookies }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser — run ig_login first" };
        const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
        const page = await ctx.newPage();
        const ok = await login(page, username, password, sessionCookies);
        if (ok) {
          const cookies = await ctx.cookies();
          return { success: true, cookies: JSON.stringify(cookies) };
        }
        await ctx.close();
        return { success: false, error: "Login failed — check credentials or verify 2FA" };
      },
    });

    api.registerTool({
      name: "ig_follow",
      description: "Follow an Instagram user by username.",
      params: {
        type: "object",
        properties: { username: { type: "string" } },
        required: ["username"],
      },
      handler: async ({ username }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser — login first with ig_login" };
        const pages = browser.pages();
        return await doFollow(pages[pages.length - 1], username);
      },
    });

    api.registerTool({
      name: "ig_unfollow",
      description: "Unfollow an Instagram user by username.",
      params: {
        type: "object",
        properties: { username: { type: "string" } },
        required: ["username"],
      },
      handler: async ({ username }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser" };
        const pages = browser.pages();
        return await doUnfollow(pages[pages.length - 1], username);
      },
    });

    api.registerTool({
      name: "ig_send_dm",
      description: "Send a direct message to an Instagram user.",
      params: {
        type: "object",
        properties: {
          username: { type: "string" },
          message: { type: "string" },
        },
        required: ["username", "message"],
      },
      handler: async ({ username, message }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser" };
        const pages = browser.pages();
        return await doSendDM(pages[pages.length - 1], username, message);
      },
    });

    api.registerTool({
      name: "ig_scrape_followers",
      description: "Scrape followers from an Instagram account.",
      params: {
        type: "object",
        properties: {
          username: { type: "string" },
          count: { type: "number", default: 100 },
        },
        required: ["username"],
      },
      handler: async ({ username, count = 100 }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser" };
        const pages = browser.pages();
        const followers = await scrapeFollowers(pages[pages.length - 1], username, count);
        return { count: followers.length, followers };
      },
    });

    api.registerTool({
      name: "ig_bombing_campaign",
      description: "Run mass follow or mass DM campaign against a list of targets.",
      params: {
        type: "object",
        properties: {
          targets: { type: "array", items: { type: "string" } },
          action: { type: "string", enum: ["follow", "dm"] },
          message: { type: "string" },
          count: { type: "number", default: 50 },
        },
        required: ["targets", "action"],
      },
      handler: async ({ targets, action, message, count = 50 }) => {
        const { browserStore } = await import("openclaw/browser");
        const browser = browserStore.current;
        if (!browser) return { error: "No browser — login first" };
        if (action === "dm" && !message) return { error: "Message required for DM" };
        const pages = browser.pages();
        const results = await runBombing(pages[pages.length - 1], targets, action, message || "", count);
        return { campaign_complete: true, action, ...results };
      },
    });
  },
});
