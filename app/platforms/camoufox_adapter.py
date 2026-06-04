import asyncio
import json
import logging
import os
import random
import time
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Page, BrowserContext

from app.platforms.base import PlatformAdapter, UserProfile, ActionResult
from app.exceptions import BlockerDetected

logger = logging.getLogger("CamoufoxAdapter")

STEALTH_PROMPT_PREFIX = (
    "Before taking any action: scroll down a little, wait 2-3 seconds, then scroll back up. "
    "Move the mouse around randomly for a moment before clicking. "
    "When typing, add small delays between characters (like a human would). "
    "Do not rush through actions — take your time. "
)

BLOCKER_SIGNALS = [
    "login page", "log in", "sign in", "sign up",
    "captcha", "verify you are human", "verification required",
    "robot check", "bot check", "security check",
    "access denied", "blocked", "suspended",
    "two-factor", "2fa", "otp",
    "sorry, this page isn't available",
    "something went wrong",
    "confirm it's you", "suspicious activity",
    "verify your account", "login required",
    "cloudflare", "checking your browser",
    "attention required", "just a moment",
]


def _get_provider_manager():
    from app.llm.provider_manager import get_provider_manager
    return get_provider_manager()


class CamoufoxAdapter(PlatformAdapter):
    """Anti-detection adapter using Camoufox (patched Firefox) + Playwright."""

    platform_name: str = "camoufox"

    def __init__(self, platform: str, **kwargs):
        self.platform = platform.lower()
        self.platform_name = platform.lower()
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._session_data: Optional[str] = None

    async def _ensure_browser(self, session_data: Optional[str] = None):
        """Launch Camoufox browser if not already running."""
        if self._page and not self._page.is_closed():
            return

        self._session_data = session_data
        proxy_config = self._get_proxy_config()

        from camoufox.async_api import AsyncCamoufox

        launch_kwargs = {
            "headless": True,
            "os": ["windows", "macos"],
        }
        if proxy_config:
            launch_kwargs["proxy"] = {
                "server": proxy_config["url"],
            }
            if proxy_config.get("username"):
                launch_kwargs["proxy"]["username"] = proxy_config["username"]
                launch_kwargs["proxy"]["password"] = proxy_config.get("password", "")

        logger.info(f"Launching Camoufox browser for {self.platform}...")
        self._camoufox = AsyncCamoufox(**launch_kwargs)
        self._context = await self._camoufox.__aenter__()

        if session_data:
            await self._load_cookies(session_data)

        self._page = await self._context.new_page()
        logger.info("Camoufox browser ready")

    async def _load_cookies(self, session_data: str):
        """Load cookies from session data into the browser context."""
        try:
            cookies = json.loads(session_data)
            if isinstance(cookies, list) and cookies:
                await self._context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    async def _get_cookies(self) -> str:
        """Export current cookies as JSON string."""
        try:
            cookies = await self._context.cookies()
            return json.dumps(cookies)
        except Exception:
            return "[]"

    @staticmethod
    def _get_proxy_config() -> Optional[dict]:
        url = os.getenv("SKYVERN_PROXY_URL", "").strip()
        if not url:
            return None
        username = os.getenv("SKYVERN_PROXY_USERNAME", "").strip()
        password = os.getenv("SKYVERN_PROXY_PASSWORD", "").strip()
        config = {"url": url}
        if username:
            config["username"] = username
            config["password"] = password
        return config

    def _check_for_blockers(self, text: str, url: str = ""):
        """Check page text for blocker signals."""
        lower = text.lower()
        for signal in BLOCKER_SIGNALS:
            if signal in lower:
                raise BlockerDetected(
                    blocker_type=signal.replace(" ", "_"),
                    message=f"Detected '{signal}' on page. Human intervention required.",
                    url=url,
                )

    async def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        """Random delay to mimic human behavior."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def _human_scroll(self):
        """Random scroll to look human."""
        for _ in range(random.randint(1, 3)):
            amount = random.randint(100, 400)
            direction = 1 if random.random() > 0.3 else -1
            await self._page.mouse.wheel(0, amount * direction)
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def _human_move_mouse(self):
        """Move mouse to a random position."""
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await self._page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.3, 0.7))

    async def _navigate(self, url: str):
        """Navigate to URL with human-like behavior."""
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self._human_delay(2, 4)
        await self._human_scroll()
        await self._human_move_mouse()

    async def _extract_page_text(self) -> str:
        """Extract visible text from the page."""
        try:
            return await self._page.inner_text("body")
        except Exception:
            return ""

    def _llm_decide(self, page_text: str, prompt: str) -> str:
        """Ask the LLM what to do based on page content."""
        pm = _get_provider_manager()
        provider = pm.get_next_provider()
        if not provider:
            return ""

        full_prompt = (
            f"You are looking at a {self.platform} page.\n"
            f"Page text (first 2000 chars): {page_text[:2000]}\n\n"
            f"Task: {prompt}\n\n"
            f"Respond with a JSON object describing what to do. "
            f"For example: {{\"action\": \"click\", \"selector\": \"button Follow\"}} or "
            f"{{\"action\": \"type\", \"selector\": \"input[name=username]\", \"text\": \"hello\"}} or "
            f"{{\"action\": \"extract\", \"data\": {{...}}}}"
        )

        try:
            import httpx
            resp = httpx.post(
                f"{provider.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {provider.config.api_key}"},
                json={
                    "model": provider.config.model_name,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return ""

    async def authenticate(self, session_data: Optional[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        try:
            await self._ensure_browser(session_data)
            home_url = f"https://www.{self.platform}.com"
            await self._navigate(home_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, home_url)
            logged_in = not any(w in text.lower() for w in ["log in", "sign in", "sign up"])
            logger.info(f"Auth check: logged_in={logged_in}")
            return logged_in
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = f"https://www.{self.platform}.com/search?q={query}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Use LLM to extract user data from page
            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} user profiles. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                users = data.get("users", [])
            except (json.JSONDecodeError, TypeError):
                users = []

            for item in users[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Search users failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Click followers button
            try:
                followers_link = self._page.locator(f'a[href*="/{handle}/followers"]').first
                await followers_link.click(timeout=5000)
                await self._human_delay(2, 4)
            except Exception:
                logger.warning("Could not find followers link, trying generic approach")

            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} follower usernames and display names. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                users = data.get("users", [])
            except (json.JSONDecodeError, TypeError):
                users = []

            for item in users[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get followers failed: {e}")
        return results

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Try clicking Follow button
            follow_btn = self._page.get_by_role("button", name="Follow").first
            await follow_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="follow")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            following_btn = self._page.get_by_role("button", name="Following").first
            await following_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="unfollow")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Try to find and click message/DM button
            msg_btn = self._page.get_by_role("button", name="Message").first
            await msg_btn.click(timeout=5000)
            await self._human_delay(2, 3)

            # Type message with human delays
            textbox = self._page.locator("textarea, div[contenteditable='true']").first
            for char in message:
                await textbox.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Send
            send_btn = self._page.get_by_role("button", name="Send").first
            await send_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="dm")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def check_inbox(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(f"https://www.{self.platform}.com/direct/inbox")
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            llm_response = self._llm_decide(
                text,
                f"Extract up to {limit} unread conversations. Return JSON: {{\"unread_conversations\": [{{\"username\": \"...\", \"latest_message\": \"...\", \"unread_count\": 1}}]}}"
            )
            try:
                data = json.loads(llm_response)
                return data.get("unread_conversations", [])[:limit]
            except (json.JSONDecodeError, TypeError):
                return []
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Check inbox failed: {e}")
            return []

    async def read_conversation(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            await self._navigate(f"https://www.{self.platform}.com/direct/t/{handle}")
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            llm_response = self._llm_decide(
                text,
                f"Extract the last {limit} messages. Return JSON: {{\"messages\": [{{\"sender\": \"me\" or \"{handle}\", \"content\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                return data.get("messages", [])[:limit]
            except (json.JSONDecodeError, TypeError):
                return []
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Read conversation failed: {e}")
            return []

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(group_id)
            text = await self._extract_page_text()
            self._check_for_blockers(text, group_id)

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} group members. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                users = data.get("users", [])
            except (json.JSONDecodeError, TypeError):
                users = []

            for item in users[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get group members failed: {e}")
        return results

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} users who commented. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                users = data.get("users", [])
            except (json.JSONDecodeError, TypeError):
                users = []

            for item in users[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get post commenters failed: {e}")
        return results

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} comments with author and text. Return JSON: {{\"comments\": [{{\"author\": \"...\", \"text\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                return data.get("comments", [])[:limit]
            except (json.JSONDecodeError, TypeError):
                return []
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get post comments failed: {e}")
            return []

    async def reply_to_comment(self, comment_id: str, message: str, post_url: Optional[str] = None) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            if post_url:
                await self._navigate(post_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url or "")

            llm_response = self._llm_decide(
                text,
                f"Find the comment by '{comment_id}' and reply with '{message}'. Return JSON: {{\"action\": \"click_reply\", \"target\": \"...\"}}"
            )
            return ActionResult(success=True, action_type="reply_comment")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="reply_comment", error=str(e))

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        handle = user_id.lstrip("@")
        try:
            await self._ensure_browser(self._session_data)
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            llm_response = self._llm_decide(
                text,
                "Extract profile info: bio, display name, follower count, recent posts. Return JSON: {\"bio\": \"...\", \"display_name\": \"...\", \"follower_count\": \"...\", \"recent_posts\": [...]}"
            )
            try:
                data = json.loads(llm_response)
            except (json.JSONDecodeError, TypeError):
                data = {}

            return {
                "username": handle,
                "bio": data.get("bio", ""),
                "display_name": data.get("display_name", ""),
                "follower_count": data.get("follower_count", ""),
                "recent_posts": data.get("recent_posts", []),
            }
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"username": handle, "bio": "", "display_name": "", "follower_count": "", "recent_posts": []}

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            llm_response = self._llm_decide(
                text,
                f"Extract the {limit} most recent posts with URLs and captions. Return JSON: {{\"posts\": [{{\"url\": \"...\", \"caption\": \"...\"}}]}}"
            )
            try:
                data = json.loads(llm_response)
                return data.get("posts", [])[:limit]
            except (json.JSONDecodeError, TypeError):
                return []
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get recent posts failed: {e}")
            return []

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            # Find comment input and type
            comment_input = self._page.locator("textarea[placeholder*='comment'], div[contenteditable='true']").first
            await comment_input.click(timeout=5000)
            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            post_btn = self._page.get_by_role("button", name="Post").first
            await post_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="comment")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Click first post
            first_post = self._page.locator("article a, div[data-e2e='user-post'] a").first
            await first_post.click(timeout=5000)
            await self._human_delay(2, 3)

            comment_input = self._page.locator("textarea[placeholder*='comment'], div[contenteditable='true']").first
            await comment_input.click(timeout=5000)
            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))

            post_btn = self._page.get_by_role("button", name="Post").first
            await post_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="comment")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def capture_screenshot(self) -> Optional[str]:
        try:
            if self._page:
                screenshot = await self._page.screenshot(type="png")
                import base64
                return base64.b64encode(screenshot).decode()
        except Exception:
            pass
        return None

    async def reply_to_dm(self, user_id: str, message: str) -> ActionResult:
        """Reply to an existing DM conversation."""
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            await self._navigate(f"https://www.{self.platform}.com/direct/t/{handle}")
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            # Find the message input box
            msg_input = self._page.locator("textarea, div[contenteditable='true'], div[data-e2e='message-input']").first
            await msg_input.click(timeout=5000)
            await self._human_delay(0.5, 1)

            # Type with human delays
            for char in message:
                await msg_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Send the message
            send_btn = self._page.get_by_role("button", name="Send").first
            await send_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="reply_dm")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="reply_dm", error=str(e))

    async def like_post(self, post_url: str) -> ActionResult:
        """Like a post."""
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            # Find and click the like/heart button
            like_btn = self._page.locator(
                "button[data-e2e='like-icon'], "
                "button[data-e2e='like-button'], "
                "span[data-e2e='like-icon'], "
                "svg[data-e2e='like-icon'], "
                "button[aria-label*='Like'], "
                "button[aria-label*='like']"
            ).first
            await like_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="like")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="like", error=str(e))

    async def unlike_post(self, post_url: str) -> ActionResult:
        """Unlike a post."""
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            unlike_btn = self._page.locator(
                "button[data-e2e='like-icon'], "
                "button[data-e2e='like-button'], "
                "span[data-e2e='like-icon'], "
                "button[aria-label*='Unlike'], "
                "button[aria-label*='unlike']"
            ).first
            await unlike_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="unlike")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="unlike", error=str(e))

    async def share_post(self, post_url: str) -> ActionResult:
        """Share/repost a post."""
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            # Click share button
            share_btn = self._page.locator(
                "button[data-e2e='share-icon'], "
                "button[data-e2e='share-button'], "
                "span[data-e2e='share-icon'], "
                "button[aria-label*='Share'], "
                "button[aria-label*='share']"
            ).first
            await share_btn.click(timeout=5000)
            await self._human_delay(1, 2)

            # Click repost option if available
            try:
                repost_btn = self._page.get_by_role("button", name="Repost").first
                await repost_btn.click(timeout=3000)
                await self._human_delay(1, 2)
            except Exception:
                # Repost might not be available, that's ok
                pass

            return ActionResult(success=True, action_type="share")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="share", error=str(e))

    async def view_stories(self, user_id: str) -> ActionResult:
        """View a user's stories."""
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Look for story circle/avatar
            story_btn = self._page.locator(
                "div[data-e2e='story-avatar'], "
                "div[data-e2e='user-avatar'][data-e2e='has-story'], "
                "a[href*='/story']"
            ).first
            await story_btn.click(timeout=5000)
            await self._human_delay(3, 5)

            # Wait for story to play, then close
            await self._human_delay(5, 7)
            try:
                close_btn = self._page.locator(
                    "button[data-e2e='close-button'], "
                    "button[aria-label='Close']"
                ).first
                await close_btn.click(timeout=3000)
            except Exception:
                pass

            return ActionResult(success=True, action_type="view_story")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="view_story", error=str(e))

    async def check_live(self, user_id: str) -> Dict[str, Any]:
        """Check if a user is currently live."""
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            is_live = "live" in text.lower() and (
                "watch" in text.lower() or "streaming" in text.lower() or "LIVE" in text
            )
            return {"username": handle, "is_live": is_live, "url": url}
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Check live failed: {e}")
            return {"username": handle, "is_live": False, "url": ""}

    async def close(self):
        """Close the browser."""
        try:
            if self._page:
                await self._page.close()
            if self._camoufox:
                await self._camoufox.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self._page = None
            self._context = None
            self._camoufox = None
