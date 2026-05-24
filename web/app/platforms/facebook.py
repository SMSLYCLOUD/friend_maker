import asyncio
import logging
import json
from typing import List, Optional
from playwright.async_api import Page, TimeoutError
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class FacebookAdapter(PlatformAdapter):
    platform_name = "facebook"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("FacebookAdapter")

    async def authenticate(self, session_data: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login using saved cookies.
        session_data should be a JSON string of cookies.
        """
        try:
            if session_data:
                cookies = json.loads(session_data)
                if isinstance(cookies, dict):
                    cookies = [cookies]
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://www.facebook.com/")

                # Check if logged in (look for home link or profile)
                try:
                    # Generic check for the main feed or navigation
                    await self.page.wait_for_selector('[role="navigation"]', timeout=10000)
                    return True
                except:
                    self.logger.warning("Session cookies might be expired or invalid.")

            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        results = []
        try:
            # Facebook Search URL
            await self.page.goto(f"https://www.facebook.com/search/people/?q={query}")
            await self.page.wait_for_selector('[role="feed"]', timeout=5000)

            # Scroll a bit to load results
            for _ in range(3):
                await self.page.mouse.wheel(0, 500)
                await self.page.wait_for_timeout(1000)

            # Scrape results
            # This relies on aria-labels or specific structures which change often.
            # We'll look for links that look like profiles.
            links = await self.page.locator('a[role="link"]').all()

            count = 0
            seen = set()
            for link in links:
                if count >= limit: break
                href = await link.get_attribute("href")
                if not href or "/groups/" in href or "/events/" in href: continue

                # Extract username/ID
                # https://www.facebook.com/zuck
                # https://www.facebook.com/profile.php?id=12345

                username = None
                if "profile.php" in href:
                    # Extract ID
                    import re
                    match = re.search(r'id=(\d+)', href)
                    if match:
                        username = match.group(1)
                else:
                    parts = href.split("facebook.com/")
                    if len(parts) > 1:
                        username = parts[1].split("/")[0].split("?")[0]

                if username and username not in seen and username not in ["watch", "marketplace", "groups", "gaming"]:
                    seen.add(username)
                    results.append(UserProfile(
                        platform_id=username,
                        username=username,
                        display_name=await link.inner_text()
                    ))
                    count += 1

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # Facebook "followers" are friends or followers depending on profile type.
        # This is very hard to scrape reliably without graph API.
        # We'll return an empty list or try best effort on the "Friends" tab if public.
        return []

    async def follow(self, user_id: str) -> ActionResult:
        # On FB this is "Add Friend" or "Follow"
        try:
            url = f"https://www.facebook.com/{user_id}"
            await self.page.goto(url)

            # Try to find "Add Friend" or "Follow" button
            # This is extremely fragile due to FB's dynamic classes.
            # We look for aria-labels.

            btn = self.page.get_by_label("Add Friend")
            if await btn.count() > 0:
                await btn.click()
                return ActionResult(success=True, action_type="add_friend")

            btn = self.page.get_by_label("Follow")
            if await btn.count() > 0:
                await btn.click()
                return ActionResult(success=True, action_type="follow")

            return ActionResult(success=False, action_type="follow", error="Button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        # Not implemented for MVP
        return ActionResult(success=False, action_type="unfollow", error="Not implemented")

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            url = f"https://www.facebook.com/{user_id}"
            await self.page.goto(url)

            msg_btn = self.page.get_by_label("Message")
            if await msg_btn.count() > 0:
                await msg_btn.click()

                # Wait for chat box
                # Again, very fragile.
                # Assuming focus moves to input
                await self.page.wait_for_selector('[role="textbox"]', timeout=5000)
                box = self.page.locator('[role="textbox"]').first
                await box.fill(message)
                await box.press("Enter")

                return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="Message button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))
