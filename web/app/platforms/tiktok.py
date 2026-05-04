import json
import logging
from typing import List
from playwright.async_api import Page
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class TiktokAdapter(PlatformAdapter):
    platform_name = "tiktok"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("TiktokAdapter")

    async def authenticate(self, session_data: str) -> bool:
        try:
            if session_data:
                cookies = json.loads(session_data)
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://www.tiktok.com/")
                try:
                    # Check for upload button or profile pic to verify auth
                    await self.page.wait_for_selector('[data-e2e="upload-icon"]', timeout=5000)
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
            await self.page.goto(f"https://www.tiktok.com/search/user?q={query}")
            await self.page.wait_for_selector('[data-e2e="search-user-info-container"]', timeout=5000)

            cells = self.page.locator('[data-e2e="search-user-info-container"]').all()
            for cell in cells[:limit]:
                text = await cell.inner_text()
                lines = text.split('\n')
                if len(lines) > 0:
                    username = lines[0]
                    display_name = lines[1] if len(lines) > 1 else None
                    results.append(UserProfile(
                        platform_id=username,
                        username=username,
                        display_name=display_name
                    ))
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # Similar logic to search, but on followers page
        return []

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.tiktok.com/@{user_id}")

            follow_btn = self.page.locator('[data-e2e="follow-button"]')

            if await follow_btn.count() > 0:
                await follow_btn.click()
                return ActionResult(success=True, action_type="follow")

            return ActionResult(success=False, action_type="follow", error="Button not found or already following")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
         try:
            await self.page.goto(f"https://www.tiktok.com/@{user_id}")
            # TikTok often changes button texts/data-e2e. Could be 'Following' state or message state.
            unfollow_btn = self.page.locator('[data-e2e="following-button"]')
            if await unfollow_btn.count() > 0:
                await unfollow_btn.click()
                return ActionResult(success=True, action_type="unfollow")
            return ActionResult(success=False, action_type="unfollow", error="Not following")
         except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.tiktok.com/@{user_id}")
            message_btn = self.page.locator('[data-e2e="message-button"]')

            if await message_btn.count() > 0:
                await message_btn.click()
                # Wait for input
                box = self.page.locator('.DraftEditor-editorContainer')
                if await box.count() > 0:
                    await box.fill(message)
                    await self.page.keyboard.press("Enter")
                    return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="DM button not found")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))
