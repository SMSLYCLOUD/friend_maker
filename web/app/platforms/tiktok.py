import json
import logging
from typing import List, Optional, Dict, Any
from playwright.async_api import Page
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class TiktokAdapter(PlatformAdapter):
    platform_name = "tiktok"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("TiktokAdapter")

    async def authenticate(self, session_data: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        try:
            if session_data:
                cookies = json.loads(session_data)
                if isinstance(cookies, dict):
                    cookies = [cookies]
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

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        self.logger.info(f"Combing TikTok (mining followers of {group_id})")
        return await self.get_followers(group_id, limit=limit)

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        self.logger.info(f"Combing TikTok commenters: {post_url}")
        # Placeholder
        return []

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments from a TikTok post"""
        self.logger.info(f"Fetching comments from TikTok post: {post_url}")
        # Placeholder implementation
        comments = []
        # TODO: Implement actual comment scraping
        return comments

    async def reply_to_comment(self, comment_id: str, message: str) -> ActionResult:
        """Reply to a specific comment on TikTok"""
        self.logger.info(f"Replying to TikTok comment {comment_id}")
        # Placeholder implementation
        # TODO: Implement actual comment reply
        return ActionResult(success=False, action_type="reply_comment", error="Not implemented")

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent posts from a TikTok user"""
        self.logger.info(f"Fetching recent posts from TikTok user: {user_id}")
        # Placeholder implementation
        posts = []
        # TODO: Implement actual post fetching
        return posts

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        """Comment on a specific TikTok post"""
        self.logger.info(f"Commenting on TikTok post: {post_url}")
        # Placeholder implementation
        # TODO: Implement actual comment posting
        return ActionResult(success=False, action_type="comment", error="Not implemented")

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        """Comment on a TikTok user's most recent post"""
        self.logger.info(f"Commenting on recent post of TikTok user: {user_id}")
        # Get user's recent posts
        posts = await self.get_user_recent_posts(user_id, limit=1)
        if not posts:
            return ActionResult(success=False, action_type="comment", error="No posts found")
        
        # Comment on the most recent post
        post_url = posts[0].get("url") if posts else None
        if not post_url:
            return ActionResult(success=False, action_type="comment", error="Could not determine post URL")
        
        return await self.comment_on_post(post_url, message)

    async def capture_screenshot(self) -> Optional[str]:
        try:
            screenshot_bytes = await self.page.screenshot(type="jpeg", quality=80)
            import base64
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            return None
