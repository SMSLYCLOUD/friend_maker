import json
import logging
from typing import List, Optional
from playwright.async_api import Page
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class SubstackAdapter(PlatformAdapter):
    platform_name = "substack"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("SubstackAdapter")

    async def authenticate(self, session_data: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        try:
            if session_data:
                cookies = json.loads(session_data)
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://substack.com/")
                try:
                    # Check for authenticated specific elements (like write button or profile dropdown)
                    await self.page.wait_for_selector('div.user-menu-button', timeout=5000)
                    return True
                except:
                    self.logger.warning("Session cookies might be expired.")
            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        results = []
        try:
            await self.page.goto(f"https://substack.com/search/{query}?focused=users")
            await self.page.wait_for_selector('div.reader2-reader-user-card', timeout=5000)

            cells = self.page.locator('div.reader2-reader-user-card').all()
            for cell in cells[:limit]:
                text = await cell.inner_text()
                lines = text.split('\n')
                if len(lines) > 0:
                    display_name = lines[0]
                    # Attempt to extract handle if present, else fallback
                    username = lines[1] if len(lines) > 1 and lines[1].startswith('@') else display_name.replace(' ', '').lower()
                    results.append(UserProfile(
                        platform_id=username,
                        username=username,
                        display_name=display_name
                    ))
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # Substack might not have a simple followers page, returning empty for now
        return []

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://substack.com/@{user_id}")

            follow_btn = self.page.locator('button.subscribe-btn')

            if await follow_btn.count() > 0:
                await follow_btn.click()
                return ActionResult(success=True, action_type="follow")

            return ActionResult(success=False, action_type="follow", error="Button not found or already following")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
         try:
            await self.page.goto(f"https://substack.com/@{user_id}")
            # Identify the unsubscribe button, it's often a dropdown or a different button state
            unfollow_btn = self.page.locator('button.subscribed-btn')
            if await unfollow_btn.count() > 0:
                await unfollow_btn.click()
                return ActionResult(success=True, action_type="unfollow")
            return ActionResult(success=False, action_type="unfollow", error="Not following")
         except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            # Substack messaging might be via chats or different mechanics, this is a placeholder
            await self.page.goto(f"https://substack.com/@{user_id}")
            message_btn = self.page.locator('button.message-btn')

            if await message_btn.count() > 0:
                await message_btn.click()
                box = self.page.locator('textarea[placeholder="Message..."]')
                if await box.count() > 0:
                    await box.fill(message)
                    await self.page.keyboard.press("Enter")
                    return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="DM button not found")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))
