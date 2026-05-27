import asyncio
import json
import logging
import os
from typing import Optional, List, Dict, Any

from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

logger = logging.getLogger("SkyvernAdapter")


class SkyvernAdapter(PlatformAdapter):
    """AI-powered platform adapter using Skyvern's vision LLMs.

    Replaces all platform-specific adapters (TikTok, Instagram, Twitter, etc.)
    with a single adapter that uses natural language prompts to interact with any website.
    Resistant to layout changes — no XPath/DOM selectors.
    """

    platform_name: str = "skyvern"

    def __init__(
        self,
        platform: str,
        skyvern_instance=None,
        skyvern_base_url: Optional[str] = None,
        skyvern_api_key: Optional[str] = None,
    ):
        self.platform = platform.lower()
        self.platform_name = platform.lower()
        self._skyvern = skyvern_instance
        self._base_url = skyvern_base_url
        self._api_key = skyvern_api_key
        self._browser = None
        self._page = None
        self._initialized = False
        self._cookies_injected = False

    async def _ensure_page(self):
        if self._page and not self._page.is_closed():
            return self._page
        from skyvern import Skyvern

        if self._skyvern is None:
            if self._base_url:
                self._skyvern = Skyvern(
                    base_url=self._base_url,
                    api_key=self._api_key or os.getenv("SKYVERN_API_KEY", ""),
                )
            else:
                self._skyvern = Skyvern.local()

        self._browser = await self._skyvern.launch_cloud_browser()
        self._page = await self._browser.get_working_page()
        return self._page

    async def _close_browser(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._page = None
            self._cookies_injected = False

    async def authenticate(
        self,
        session_data: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        page = await self._ensure_page()
        try:
            home_url = f"https://www.{self.platform}.com"
            await page.goto(home_url, timeout=30000)

            if session_data:
                try:
                    cookies = json.loads(session_data)
                    if isinstance(cookies, dict):
                        cookies = [cookies]
                    await page.context.add_cookies(cookies)
                    await page.goto(home_url, timeout=30000)
                except Exception as e:
                    logger.warning(f"Cookie injection failed, trying AI login: {e}")

            is_logged_in = await page.validate(
                f"Check if I am logged in to {self.platform}. Look for profile icon, avatar, or user menu."
            )
            if is_logged_in:
                self._cookies_injected = True
                return True

            if username and password:
                await page.act(
                    f"Log in to {self.platform} with username '{username}' and password '{password}'. "
                    "Wait for the home page to load after login."
                )
                is_logged_in = await page.validate(
                    f"Check if login to {self.platform} was successful."
                )
                return bool(is_logged_in)

            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        page = await self._ensure_page()
        results = []
        try:
            await page.goto(f"https://www.{self.platform}.com/search?q={query}", timeout=30000)
            data = await page.extract(
                f"Find the first {limit} user profiles in the search results. "
                "For each user, get their username and display name.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "display_name": {"type": "string"},
                        },
                    },
                },
            )
            if data:
                for item in data[:limit]:
                    results.append(
                        UserProfile(
                            platform_id=item.get("username", ""),
                            username=item.get("username", ""),
                            display_name=item.get("display_name"),
                        )
                    )
        except Exception as e:
            logger.error(f"Search users on {self.platform} failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        page = await self._ensure_page()
        results = []
        try:
            await page.goto(
                f"https://www.{self.platform}.com/@{user_id}/followers", timeout=30000
            )
            data = await page.extract(
                f"Get the first {limit} followers from this list. Return their usernames and display names.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "display_name": {"type": "string"},
                        },
                    },
                },
            )
            if data:
                for item in data[:limit]:
                    results.append(
                        UserProfile(
                            platform_id=item.get("username", ""),
                            username=item.get("username", ""),
                            display_name=item.get("display_name"),
                        )
                    )
        except Exception as e:
            logger.error(f"Get followers on {self.platform} failed: {e}")
        return results

    async def follow(self, user_id: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.goto(f"https://www.{self.platform}.com/@{user_id}", timeout=30000)
            await page.act("Click the follow button to follow this user.")
            return ActionResult(success=True, action_type="follow")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.goto(f"https://www.{self.platform}.com/@{user_id}", timeout=30000)
            await page.act("Click the unfollow or following button to unfollow this user.")
            return ActionResult(success=True, action_type="unfollow")
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.act(
                f"Go to the messages or DM section, start a conversation with @{user_id}, "
                f"type the following message: '{message}', and send it."
            )
            return ActionResult(success=True, action_type="dm")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        page = await self._ensure_page()
        results = []
        try:
            await page.goto(group_id, timeout=30000)
            data = await page.extract(
                f"Get the first {limit} members from this group or community. "
                "Return their usernames and display names.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "display_name": {"type": "string"},
                        },
                    },
                },
            )
            if data:
                for item in data[:limit]:
                    results.append(
                        UserProfile(
                            platform_id=item.get("username", ""),
                            username=item.get("username", ""),
                            display_name=item.get("display_name"),
                        )
                    )
        except Exception as e:
            logger.error(f"Get group members on {self.platform} failed: {e}")
        return results

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        page = await self._ensure_page()
        results = []
        try:
            await page.goto(post_url, timeout=30000)
            data = await page.extract(
                f"Get the first {limit} users who commented on this post. "
                "Return their usernames and display names.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "display_name": {"type": "string"},
                        },
                    },
                },
            )
            if data:
                for item in data[:limit]:
                    results.append(
                        UserProfile(
                            platform_id=item.get("username", ""),
                            username=item.get("username", ""),
                            display_name=item.get("display_name"),
                        )
                    )
        except Exception as e:
            logger.error(f"Get post commenters on {self.platform} failed: {e}")
        return results

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        page = await self._ensure_page()
        try:
            await page.goto(post_url, timeout=30000)
            data = await page.extract(
                f"Get the first {limit} comments on this post. "
                "For each comment, get the author username and comment text.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string"},
                            "text": {"type": "string"},
                        },
                    },
                },
            )
            return data[:limit] if data else []
        except Exception as e:
            logger.error(f"Get post comments on {self.platform} failed: {e}")
            return []

    async def reply_to_comment(self, comment_id: str, message: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.act(f"Find the comment with id '{comment_id}', click reply, "
                           f"type '{message}', and submit the reply.")
            return ActionResult(success=True, action_type="reply_comment")
        except Exception as e:
            return ActionResult(success=False, action_type="reply_comment", error=str(e))

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        page = await self._ensure_page()
        try:
            await page.goto(f"https://www.{self.platform}.com/@{user_id}", timeout=30000)
            data = await page.extract(
                f"Get the {limit} most recent posts by this user. "
                "For each post, get the post URL, caption or title, and engagement stats.",
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "caption": {"type": "string"},
                        },
                    },
                },
            )
            return data[:limit] if data else []
        except Exception as e:
            logger.error(f"Get recent posts on {self.platform} failed: {e}")
            return []

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.goto(post_url, timeout=30000)
            await page.act(f"Type the comment '{message}' in the comment box and submit it.")
            return ActionResult(success=True, action_type="comment")
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        page = await self._ensure_page()
        try:
            await page.goto(f"https://www.{self.platform}.com/@{user_id}", timeout=30000)
            await page.act(
                f"Find the most recent post by this user, "
                f"type the comment '{message}' in the comment box, and submit it."
            )
            return ActionResult(success=True, action_type="comment")
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def capture_screenshot(self) -> Optional[str]:
        page = await self._ensure_page()
        try:
            screenshot_bytes = await self._page.screenshot(type="jpeg", quality=80)
            import base64

            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
