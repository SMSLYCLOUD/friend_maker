import json
import logging
from typing import List, Optional
from playwright.async_api import Page
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class TwitterAdapter(PlatformAdapter):
    platform_name = "twitter"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("TwitterAdapter")

    async def authenticate(self, session_data: Optional[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        try:
            if session_data:
                cookies = json.loads(session_data)
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://twitter.com/home")
                try:
                    # Check for tweet box or nav bar
                    await self.page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=5000)
                    return True
                except:
                    self.logger.warning("Session cookies might be expired. Trying credentials...")

            if username and password:
                await self.page.goto("https://twitter.com/i/flow/login")
                
                # Fill username
                await self.page.wait_for_selector('input[autocomplete="username"]')
                await self.page.fill('input[autocomplete="username"]', username)
                await self.page.keyboard.press("Enter")
                
                # Twitter sometimes asks for unusual activity (phone/email check)
                # But for standard flow:
                await self.page.wait_for_selector('input[name="password"]')
                await self.page.fill('input[name="password"]', password)
                await self.page.get_by_role("button", name="Log in").click()

                try:
                    await self.page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=15000)
                    return True
                except:
                    self.logger.error("Twitter login failed or requires manual intervention (2FA/Verification).")
                    return False

            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        results = []
        try:
            # Go to search
            await self.page.goto(f"https://twitter.com/search?q={query}&src=typed_query&f=user")
            await self.page.wait_for_selector('[data-testid="UserCell"]', timeout=5000)

            # .all() is synchronous
            cells = self.page.locator('[data-testid="UserCell"]').all()
            for cell in cells[:limit]:
                # Extract username
                # Usually inside a link with href starting with /
                # Simplified extraction
                text = await cell.inner_text()
                lines = text.split('\n')
                # Heuristic: Handle starts with @
                handle = next((line for line in lines if line.startswith('@')), None)
                if handle:
                    username = handle.strip('@')
                    results.append(UserProfile(
                        platform_id=username,
                        username=username,
                        display_name=lines[0] if lines else None
                    ))
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # Similar logic to search, but on followers page
        return []

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://twitter.com/{user_id}")

            # Follow button logic
            # Twitter buttons are tricky, look for specific testid
            follow_btn = self.page.locator(f'[data-testid$="-follow"]')

            if await follow_btn.count() > 0:
                await follow_btn.click()
                return ActionResult(success=True, action_type="follow")

            return ActionResult(success=False, action_type="follow", error="Button not found or already following")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
         try:
            await self.page.goto(f"https://twitter.com/{user_id}")
            unfollow_btn = self.page.locator(f'[data-testid$="-unfollow"]')
            if await unfollow_btn.count() > 0:
                await unfollow_btn.click()
                # Confirm dialog
                confirm = self.page.locator('[data-testid="confirmationSheetConfirm"]')
                if await confirm.count() > 0:
                    await confirm.click()
                return ActionResult(success=True, action_type="unfollow")
            return ActionResult(success=False, action_type="unfollow", error="Not following")
         except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self.page.goto(f"https://twitter.com/{user_id}")
            dm_btn = self.page.locator('[data-testid="sendDMFromProfile"]')

            if await dm_btn.count() > 0:
                await dm_btn.click()
                # Wait for input
                box = self.page.locator('[data-testid="dmComposerTextInput"]')
                await box.fill(message)
                await box.press("Enter")
                return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="DM closed")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        """Scrape members from a Twitter Community"""
        self.logger.info(f"Combing Twitter Community: {group_id}")
        # Placeholder: Navigate to community members page and scrape
        return []

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        """Scrape users who replied to a tweet"""
        self.logger.info(f"Combing Tweet replies: {post_url}")
        # Placeholder: Navigate to tweet and scrape user cells from replies
        return []

    async def capture_screenshot(self) -> Optional[str]:
        try:
            return await self.page.screenshot(type="jpeg", quality=50, full_page=False, encoding="base64")
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            return None
