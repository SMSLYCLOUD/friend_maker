import asyncio
import logging
import json
from typing import List, Optional
from playwright.async_api import Page, TimeoutError
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class InstagramAdapter(PlatformAdapter):
    platform_name = "instagram"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("InstagramAdapter")

    async def authenticate(self, session_data: str) -> bool:
        """
        Login using saved cookies.
        session_data should be a JSON string of cookies.
        """
        try:
            if session_data:
                cookies = json.loads(session_data)
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://www.instagram.com/")
                # Check if logged in (e.g. check for profile icon or absence of login form)
                try:
                    await self.page.wait_for_selector('a[href="#"]', timeout=5000) # Generic home/nav link
                    return True
                except:
                    # If failed, maybe cookies expired
                    self.logger.warning("Session cookies might be expired.")

            # If no session or invalid, we wait for user manual login (in the real app)
            # But for automation flow, we return False if session is invalid.
            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def get_current_cookies(self) -> str:
        cookies = await self.page.context.cookies()
        return json.dumps(cookies)

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        results = []
        try:
            # Click search
            # Note: Selectors are fragile. Using aria-labels is often better.
            search_icon = self.page.get_by_role("link", name="Search")
            if await search_icon.count() > 0:
                await search_icon.click()
            else:
                # Try mobile layout or different view
                await self.page.goto(f"https://www.instagram.com/explore/search/keyword/?q={query}")

            input_box = self.page.get_by_placeholder("Search")
            await input_box.fill(query)
            await self.page.wait_for_timeout(2000) # Wait for results

            # Scrape results
            # This is a simplification. Real scraping needs robust loop.
            # Assuming a list of results appears
            links = await self.page.query_selector_all('a[href^="/"][role="link"]')

            count = 0
            for link in links:
                if count >= limit: break
                href = await link.get_attribute("href")
                username = href.strip("/").split("/")[0] # Rough extraction

                # Filter out non-user links
                if username in ["explore", "reels", "direct"]: continue

                results.append(UserProfile(
                    platform_id=username, # Use username as ID for IG
                    username=username,
                    display_name=username # Placeholder
                ))
                count += 1

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # This is complex in IG. Needs clicking "Followers" and scrolling.
        followers = []
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            # Click followers link
            await self.page.get_by_text("followers").click()
            await self.page.wait_for_selector('div[role="dialog"]', timeout=5000)

            dialog = self.page.locator('div[role="dialog"]')
            # Scroll loop would go here

            # Placeholder scraping
            # In a real impl, we'd scroll the list inside the dialog.
            # For this Phase, I will just grab what's visible.
            items = await dialog.locator('a[href^="/"]').all()
            for item in items:
                href = await item.get_attribute("href")
                u = href.strip("/")
                followers.append(UserProfile(platform_id=u, username=u))
                if len(followers) >= limit: break

        except Exception as e:
            self.logger.error(f"Get followers failed: {e}")

        return followers

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            # Look for Follow button
            # It could be "Follow", "Requested", "Following"
            btn = self.page.get_by_role("button", name="Follow", exact=True)

            if await btn.count() > 0:
                await btn.click()
                # Verify change to "Following" or "Requested"
                # await expect(btn).not_to_be_visible()
                return ActionResult(success=True, action_type="follow")
            else:
                return ActionResult(success=False, action_type="follow", error="Already following or button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            btn = self.page.get_by_role("button", name="Following")
            if await btn.count() > 0:
                await btn.click()
                # Confirm dialog often appears
                unfollow_confirm = self.page.get_by_role("button", name="Unfollow")
                if await unfollow_confirm.count() > 0:
                    await unfollow_confirm.click()
                return ActionResult(success=True, action_type="unfollow")

            return ActionResult(success=False, action_type="unfollow", error="Not following")

        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            # Go to profile, click Message
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            msg_btn = self.page.get_by_role("button", name="Message")
            if await msg_btn.count() > 0:
                await msg_btn.click()

                # Wait for chat box
                box = self.page.get_by_role("textbox", name="Message")
                await box.fill(message)
                await box.press("Enter")

                return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="Message button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))
