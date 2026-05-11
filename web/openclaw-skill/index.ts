import { registerHook } from "openclaw-plugin-sdk/hooks";
import { browserStore } from "openclaw-plugin-sdk/browser";

interface IGCredentials {
  username: string;
  password: string;
  sessionCookies?: string;
}

interface CampaignTarget {
  target_username?: string;
  target_hashtag?: string;
  target_list?: string[];
}

interface CampaignConfig {
  action: "follow" | "dm" | "scrape_followers" | "scrape_commenters" | "bombing" | "unfollow";
  target: CampaignTarget;
  count?: number;
  message?: string;
  credentials: IGCredentials;
}

const IG_URLS = {
  login: "https://www.instagram.com/accounts/login/",
  home: "https://www.instagram.com/",
  search: "https://www.instagram.com/search/",
  followers: (username: string) => `https://www.instagram.com/${username}/followers/`,
  following: (username: string) => `https://www.instagram.com/${username}/following/`,
  profile: (username: string) => `https://www.instagram.com/${username}/`,
  post: (url: string) => url,
};

async function loginToInstagram(page: any, username: string, password: string, cookies?: string): Promise<boolean> {
  const browser = browserStore.current;
  if (!browser) {
    return { success: false, error: "No browser session available" } as any;
  }

  if (cookies) {
    try {
      const parsedCookies = JSON.parse(cookies);
      await page.context.add_cookies(parsedCookies);
      await page.goto(IG_URLS.home);
      await page.wait_for_timeout(3000);
      const logged_in = await page.locator('svg[aria-label="New post"]').count() > 0;
      if (logged_in) {
        console.log("[IG] Session restored from cookies");
        return true;
      }
    } catch {
      console.log("[IG] Cookie restore failed, falling back to login");
    }
  }

  await page.goto(IG_URLS.login, { timeout: 30000 });
  await page.wait_for_load_state("domcontentloaded");
  await page.wait_for_timeout(3000);

  const usernameField = page.locator('input[name="username"]');
  await usernameField.waitFor({ timeout: 10000 });
  await usernameField.fill(username);
  await page.wait_for_timeout(500);

  const nextBtn = page.locator('button:has-text("Next")');
  if (await nextBtn.count() > 0) {
    await nextBtn.click();
    await page.wait_for_timeout(1000);
  }

  const passwordField = page.locator('input[name="password"]');
  await passwordField.waitFor({ timeout: 5000 });
  await passwordField.fill(password);
  await page.wait_for_timeout(500);

  await page.locator('button[type="submit"]').click();
  await page.wait_for_timeout(5000);

  try {
    await page.wait_for_selector('svg[aria-label="New post"]', { timeout: 15000 });
    const cookies = await page.context.cookies();
    console.log("[IG] Login successful");
    return true;
  } catch {
    console.log("[IG] Login failed — may need verification");
    return false;
  }
}

async function doFollow(page: any, targetUsername: string): Promise<{ success: boolean; error?: string }> {
  await page.goto(IG_URLS.profile(targetUsername), { timeout: 20000 });
  await page.wait_for_timeout(2000);

  const followBtn = page.locator('button:has-text("Follow")');
  const followingBtn = page.locator('button:has-text("Following")');

  if (await followingBtn.count() > 0) {
    return { success: true };
  }

  if (await followBtn.count() > 0) {
    await followBtn.click();
    await page.wait_for_timeout(1000);
    return { success: true };
  }

  return { success: false, error: "Follow button not found" };
}

async function doUnfollow(page: any, targetUsername: string): Promise<{ success: boolean; error?: string }> {
  await page.goto(IG_URLS.profile(targetUsername), { timeout: 20000 });
  await page.wait_for_timeout(2000);

  const followingBtn = page.locator('button:has-text("Following")');
  if (await followingBtn.count() > 0) {
    await followingBtn.click();
    await page.wait_for_timeout(500);
    const confirmBtn = page.locator('button:has-text("Unfollow")');
    if (await confirmBtn.count() > 0) {
      await confirmBtn.click();
      await page.wait_for_timeout(1000);
      return { success: true };
    }
  }

  return { success: false, error: "Not following or button not found" };
}

async function doSendDM(page: any, targetUsername: string, message: string): Promise<{ success: boolean; error?: string }> {
  await page.goto(IG_URLS.profile(targetUsername), { timeout: 20000 });
  await page.wait_for_timeout(2000);

  const messageBtn = page.locator('button:has-text("Message")');
  if (await messageBtn.count() > 0) {
    await messageBtn.click();
    await page.wait_for_timeout(1500);

    const textbox = page.locator('div[contenteditable="true"][role="textbox"], textarea[name="message"]');
    await textbox.waitFor({ timeout: 5000 });
    await textbox.fill(message);
    await textbox.press("Enter");
    await page.wait_for_timeout(1000);
    return { success: true };
  }

  return { success: false, error: "Message button not found" };
}

async function scrapeFollowers(page: any, targetUsername: string, count: number = 100): Promise<string[]> {
  await page.goto(IG_URLS.followers(targetUsername), { timeout: 20000 });
  await page.wait_for_timeout(2000);

  const dialog = page.locator('div[role="dialog"]');
  const scrollable = dialog.locator('div[style*="overflow"]');

  let scraped: string[] = [];
  let lastCount = 0;

  for (let i = 0; i < count / 10 && scraped.length < count; i++) {
    if (scrollable.count() > 0) {
      await scrollable.last().evaluate((el: any) => el.scrollTop += 500);
    } else {
      await page.evaluate(() => window.scrollBy(0, 500));
    }
    await page.wait_for_timeout(800);

    const links = await dialog.locator('a[href*="/"]').all();
    for (const link of links) {
      const href = await link.getAttribute("href");
      const u = href?.replace("/", "").replace(/\/$/, "").split("?")[0];
      if (u && u !== targetUsername && !scraped.includes(u)) {
        scraped.push(u);
      }
      if (scraped.length >= count) break;
    }

    if (scraped.length === lastCount && i > 3) break;
    lastCount = scraped.length;
  }

  return scraped;
}

async function runBombingCampaign(
  page: any,
  targets: string[],
  action: "follow" | "dm",
  message: string,
  count: number
): Promise<{ processed: number; succeeded: number; failed: string[] }> {
  let succeeded = 0;
  let failed: string[] = [];

  for (const target of targets.slice(0, count)) {
    try {
      let result: { success: boolean; error?: string };

      if (action === "follow") {
        result = await doFollow(page, target);
      } else {
        result = await doSendDM(page, target, message);
      }

      if (result.success) {
        succeeded++;
      } else {
        failed.push(`${target}: ${result.error}`);
      }

      const delay = 3000 + Math.random() * 4000;
      await page.wait_for_timeout(delay);

    } catch (err) {
      failed.push(`${target}: ${err}`);
    }
  }

  return { processed: targets.length, succeeded, failed };
}

export { loginToInstagram, doFollow, doUnfollow, doSendDM, scrapeFollowers, runBombingCampaign };

registerHook("tools/register", async (tools) => {
  tools.register({
    name: "ig_login",
    description: "Log into Instagram account. Returns session cookies for reuse.",
    params: {
      type: "object",
      properties: {
        username: { type: "string", description: "Instagram username or email" },
        password: { type: "string", description: "Instagram password" },
        sessionCookies: { type: "string", description: "Optional JSON session cookies for fast restore" },
      },
      required: ["username", "password"],
    },
    handler: async ({ username, password, sessionCookies }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser available" };
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page = await ctx.newPage();
      const success = await loginToInstagram(page, username, password, sessionCookies);
      if (success) {
        const cookies = await ctx.cookies();
        return { success: true, cookies: JSON.stringify(cookies) };
      }
      await ctx.close();
      return { success: false, error: "Login failed — check credentials or verify 2FA" };
    },
  });

  tools.register({
    name: "ig_follow",
    description: "Follow an Instagram user by their username.",
    params: {
      type: "object",
      properties: {
        username: { type: "string", description: "Instagram username to follow" },
      },
      required: ["username"],
    },
    handler: async ({ username }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser — run ig_login first" };
      const pages = browser.pages();
      const page = pages[pages.length - 1];
      const result = await doFollow(page, username);
      return result;
    },
  });

  tools.register({
    name: "ig_unfollow",
    description: "Unfollow an Instagram user by their username.",
    params: {
      type: "object",
      properties: {
        username: { type: "string", description: "Instagram username to unfollow" },
      },
      required: ["username"],
    },
    handler: async ({ username }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser" };
      const pages = browser.pages();
      const page = pages[pages.length - 1];
      return await doUnfollow(page, username);
    },
  });

  tools.register({
    name: "ig_send_dm",
    description: "Send a direct message to an Instagram user.",
    params: {
      type: "object",
      properties: {
        username: { type: "string", description: "Instagram username to DM" },
        message: { type: "string", description: "Message text to send" },
      },
      required: ["username", "message"],
    },
    handler: async ({ username, message }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser" };
      const pages = browser.pages();
      const page = pages[pages.length - 1];
      return await doSendDM(page, username, message);
    },
  });

  tools.register({
    name: "ig_scrape_followers",
    description: "Scrape followers from an Instagram account. Returns a list of usernames.",
    params: {
      type: "object",
      properties: {
        username: { type: "string", description: "Account whose followers to scrape" },
        count: { type: "number", description: "Max followers to scrape (default 100)", default: 100 },
      },
      required: ["username"],
    },
    handler: async ({ username, count = 100 }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser" };
      const pages = browser.pages();
      const page = pages[pages.length - 1];
      const followers = await scrapeFollowers(page, username, count);
      return { count: followers.length, followers };
    },
  });

  tools.register({
    name: "ig_bombing_campaign",
    description: "Run a mass follow or mass DM campaign against a list of targets. This is the main automation for social growth.",
    params: {
      type: "object",
      properties: {
        targets: {
          type: "array",
          items: { type: "string" },
          description: "List of Instagram usernames to target",
        },
        action: { type: "string", enum: ["follow", "dm"], description: "follow or dm" },
        message: { type: "string", description: "DM message text (required if action is dm)" },
        count: { type: "number", description: "Max actions to perform (default 50)", default: 50 },
      },
      required: ["targets", "action"],
    },
    handler: async ({ targets, action, message, count = 50 }) => {
      const browser = browserStore.current;
      if (!browser) return { error: "No browser — login first with ig_login" };
      if (action === "dm" && !message) return { error: "Message required for DM action" };

      const pages = browser.pages();
      const page = pages[pages.length - 1];

      const results = await runBombingCampaign(page, targets, action, message || "", count);

      return {
        campaign_complete: true,
        action,
        ...results,
        summary: `${results.succeeded}/${results.processed} ${action} actions succeeded`,
      };
    },
  });
});
