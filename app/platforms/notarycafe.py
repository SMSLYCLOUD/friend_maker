"""
NotaryCafe.com automation module.
Uses Playwright directly for browser-based interaction.
"""
import logging

logger = logging.getLogger(__name__)

async def nc_login(page, email: str, password: str) -> bool:
    base = "https://www.notarycafe.com"
    await page.goto(f"{base}/login", timeout=30000)
    await page.wait_for_timeout(2000)
    await page.fill('input[name="email"], input[type="email"]', email)
    await page.fill('input[name="password"], input[type="password"]', password)
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_timeout(3000)
    url = page.url
    return "dashboard" in url or "profile" in url or url == base + "/"

async def nc_search(page, location: str) -> list:
    base = "https://www.notarycafe.com"
    await page.goto(f"{base}/find-a-notary", timeout=30000)
    await page.wait_for_timeout(2000)
    search_box = page.locator('#SearchString')
    await search_box.wait_for(timeout=5000)
    await search_box.fill(location)
    await search_box.press("Enter")
    await page.wait_for_timeout(3000)
    results = []
    cards = await page.locator('[class*="profile"], [class*="card"], [class*="result"]').all()
    for card in cards[:20]:
        name = await card.locator('[class*="name"], h2, h3, h4').first().text_content() or ""
        loc = await card.locator('[class*="location"], [class*="city"]').first().text_content() or ""
        link = await card.locator("a").first().get_attribute("href") or ""
        if name.strip():
            results.append({"name": name.strip(), "location": loc.strip(), "url": link})
    return results or [{"message": "No results found"}]

async def nc_scrape_profile(page, profile_url: str) -> dict:
    base = "https://www.notarycafe.com"
    url = profile_url if profile_url.startswith("http") else base + profile_url
    await page.goto(url, timeout=30000)
    await page.wait_for_timeout(2000)
    name = await page.locator('[class*="name"], h1, h2').first().text_content() or ""
    loc = await page.locator('[class*="location"], [class*="city"]').first().text_content() or ""
    about = await page.locator('[class*="about"], [class*="bio"]').first().text_content() or ""
    return {"name": name.strip(), "location": loc.strip(), "about": about.strip(), "url": page.url}

async def nc_send_message(page, profile_url: str, message: str) -> dict:
    base = "https://www.notarycafe.com"
    url = profile_url if profile_url.startswith("http") else base + profile_url
    await page.goto(url, timeout=30000)
    await page.wait_for_timeout(2000)
    msg_btn = page.locator('a[href*="message"], button:has-text("Message"), a:has-text("Contact")').first()
    if await msg_btn.count() > 0:
        await msg_btn.click()
        await page.wait_for_timeout(2000)
    textarea = page.locator("textarea, [contenteditable='true'], [role='textbox']").first()
    if await textarea.count() > 0:
        await textarea.fill(message)
        await page.locator('button[type="submit"], button:has-text("Send")').first().click()
        await page.wait_for_timeout(2000)
        return {"success": True}
    return {"success": False, "error": "Message form not found"}
