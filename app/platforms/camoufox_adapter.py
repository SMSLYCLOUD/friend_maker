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
        self._camoufox = None

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

        logger.info(f"Launching Camoufox browser for {self.platform}...")
        self._camoufox = AsyncCamoufox(**launch_kwargs)
        try:
            self._context = await self._camoufox.__aenter__()
        except Exception as e:
            logger.warning(f"Camoufox launch failed, retrying without proxy: {e}")
            self._camoufox = AsyncCamoufox(headless=True, os=["windows", "macos"])
            self._context = await self._camoufox.__aenter__()

        # Camoufox may return Browser or BrowserContext — get the context either way
        if hasattr(self._context, 'new_context'):
            self._context = await self._context.new_context()

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

    async def _run_with_retry(self, fn, *args, **kwargs):
        """Run a function, restarting the browser if it died."""
        for attempt in range(3):
            try:
                if self._page and self._page.is_closed():
                    logger.warning("Page closed, restarting browser...")
                    await self._ensure_browser(self._session_data)
                return await fn(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                is_browser_dead = (
                    "closed" in error_str
                    or "disconnected" in error_str
                    or "handler is closed" in error_str
                    or "target closed" in error_str
                )
                is_nav_abort = "ns_binding_aborted" in error_str
                if (is_browser_dead or is_nav_abort) and attempt < 2:
                    logger.warning(f"Navigation failed (attempt {attempt + 1}): {e}")
                    if is_browser_dead:
                        self._page = None
                        self._context = None
                        await self._ensure_browser(self._session_data)
                    else:
                        await self._human_delay(3, 5)
                    continue
                raise

    @staticmethod
    def _get_proxy_config() -> Optional[dict]:
        url = os.getenv("SKYVERN_PROXY_URL", "").strip()
        if not url:
            return None
        # Ensure scheme is present for Firefox
        if not url.startswith(("http://", "https://", "socks5://")):
            url = f"http://{url}"
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
        async def _do_navigate():
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)
            await self._human_scroll()
            await self._human_move_mouse()
        await self._run_with_retry(_do_navigate)

    async def _extract_page_text(self) -> str:
        """Extract visible text from the page."""
        async def _do_extract():
            try:
                return await self._page.inner_text("body")
            except Exception:
                return ""
        return await self._run_with_retry(_do_extract)

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
                    "model": provider.config.model,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.3,
                },
                timeout=120,
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

            # Navigate directly to followers page
            url = f"https://www.{self.platform}.com/@{handle}/followers"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Scroll down to load more followers (TikTok lazy-loads heavily)
            prev_count = 0
            for i in range(15):
                await self._page.mouse.wheel(0, 1500)
                await self._human_delay(1.5, 2.5)
                # Count current links to detect if new content loaded
                links = await self._page.query_selector_all('a[href*="/@"]')
                curr_count = len(links)
                if curr_count == prev_count and i > 3:
                    break  # No new content loaded, stop scrolling
                prev_count = curr_count

            text = await self._extract_page_text()

            # Try to extract usernames from page HTML
            usernames = []
            try:
                links = await self._page.query_selector_all('a[href*="/@"]')
                for link in links[:limit * 2]:
                    href = await link.get_attribute("href")
                    if href and "/@" in href:
                        username = href.split("/@")[-1].split("/")[0].split("?")[0]
                        if username and username not in usernames and len(username) > 1:
                            usernames.append(username)
            except Exception as e:
                logger.warning(f"HTML extraction failed: {e}")

            # If HTML extraction got results, use them
            if usernames:
                for u in usernames[:limit]:
                    results.append(UserProfile(platform_id=u, username=u))
                logger.info(f"Extracted {len(results)} followers from HTML")
            else:
                # Fallback to LLM
                llm_response = self._llm_decide(
                    text,
                    f"Extract follower usernames from this TikTok followers page. Return JSON: {{\"usernames\": [\"user1\", \"user2\"]}}"
                )
                try:
                    data = json.loads(llm_response)
                    for u in data.get("usernames", [])[:limit]:
                        results.append(UserProfile(platform_id=u, username=u))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("LLM extraction also failed")

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
            await follow_btn.click(timeout=15000)
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
            await following_btn.click(timeout=15000)
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
            logger.info(f"send_dm: Navigating to {url}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Close any modal overlays that might block clicks
            try:
                await self._page.keyboard.press("Escape")
                await self._human_delay(1, 2)
            except: pass

            # Check if Message button exists
            msg_btn = self._page.get_by_role("button", name="Message").first
            try:
                await msg_btn.wait_for(state="visible", timeout=10000)
            except:
                logger.info(f"send_dm: No Message button found for @{handle}")
                return ActionResult(success=False, action_type="dm", error="No Message button found")

            logger.info(f"send_dm: Clicking Message button for @{handle}")
            await msg_btn.click(timeout=15000, force=True)
            await self._human_delay(3, 5)

            # Check current URL after clicking
            current_url = self._page.url
            logger.info(f"send_dm: After click, URL is: {current_url}")

            # If navigated to inbox, try to find the chat with this user
            if "/direct/inbox" in current_url:
                logger.info(f"send_dm: On inbox page, looking for chat with @{handle}")
                # Try to find and click on the user's chat in inbox
                try:
                    chat_link = self._page.get_by_text(handle).first
                    await chat_link.click(timeout=10000)
                    await self._human_delay(2, 3)
                except:
                    logger.warning(f"send_dm: Could not find chat with @{handle} in inbox")
                    return ActionResult(success=False, action_type="dm", error="Chat not found in inbox")

            # Now look for the textbox
            textbox = self._page.locator("textarea, div[contenteditable='true']").first
            try:
                await textbox.wait_for(state="visible", timeout=10000)
            except:
                logger.warning(f"send_dm: Textbox not found on {self._page.url}")
                return ActionResult(success=False, action_type="dm", error="Textbox not found")

            logger.info(f"send_dm: Typing message ({len(message)} chars)")
            for char in message:
                await textbox.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Send
            send_btn = self._page.get_by_role("button", name="Send").first
            logger.info(f"send_dm: Clicking Send button")
            await send_btn.click(timeout=15000)
            await self._human_delay(1, 2)
            logger.info(f"send_dm: DM sent to @{handle}")
            return ActionResult(success=True, action_type="dm")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"send_dm FAILED for @{handle}: {e}")
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
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Infinite scroll until no new comment links load
            prev_count = 0
            for i in range(100):
                await self._page.mouse.wheel(0, 1200)
                await self._human_delay(1.5, 2.5)
                links = await self._page.query_selector_all('a[href*="/@"]')
                curr_count = len(links)
                if curr_count == prev_count and i > 2:
                    break
                prev_count = curr_count

            # Extract commenters from HTML
            try:
                links = await self._page.query_selector_all('a[href*="/@"]')
                for link in links[:limit * 3]:
                    href = await link.get_attribute("href")
                    if href and "/@" in href:
                        username = href.split("/@")[-1].split("/")[0].split("?")[0]
                        if username and len(username) > 1:
                            results.append(UserProfile(platform_id=username, username=username))
                            if len(results) >= limit:
                                break
                if results:
                    logger.info(f"Extracted {len(results)} commenters from HTML")
                    return results
            except Exception as e:
                logger.warning(f"HTML commenter extraction failed: {e}")

            # Fallback to LLM
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} users who commented on this post. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\"}}]}}"
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
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Check if account is private
            is_private = False
            private_indicators = ["This account is private", "This account's posts are hidden", "Private account"]
            for indicator in private_indicators:
                if indicator.lower() in text.lower():
                    is_private = True
                    break

            # Also check for lock icon (TikTok private indicator)
            try:
                lock = await self._page.query_selector('[data-e2e="private-account"], .private-account, [aria-label*="private"]')
                if lock:
                    is_private = True
            except: pass

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
                "is_private": is_private,
            }
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"username": handle, "bio": "", "display_name": "", "follower_count": "", "recent_posts": [], "is_private": False}

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Scroll to load posts (TikTok lazy-loads)
            for _ in range(5):
                await self._page.mouse.wheel(0, 1200)
                await self._human_delay(1.5, 2.5)

            # Try HTML extraction first — look for post links
            posts = []
            try:
                links = await self._page.query_selector_all('a[href*="/video/"], a[href*="/photo/"]')
                seen_ids = set()
                for link in links[:limit * 5]:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    # Extract video/photo ID for dedup
                    import re
                    vid_match = re.search(r'/(video|photo)/(\d+)', href)
                    if not vid_match:
                        continue
                    vid_id = vid_match.group(2)
                    if vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)
                    if not href.startswith("http"):
                        href = f"https://www.{self.platform}.com{href}"
                    posts.append({"url": href, "caption": ""})
                    if len(posts) >= limit:
                        break
                if posts:
                    logger.info(f"Extracted {len(posts)} posts from HTML for @{handle}")
                    return posts
            except Exception as e:
                logger.warning(f"HTML post extraction failed: {e}")

            # Fallback to LLM
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
            await comment_input.click(timeout=15000)
            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            post_btn = self._page.get_by_role("button", name="Post").first
            await post_btn.click(timeout=15000)
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
            await first_post.click(timeout=15000)
            await self._human_delay(2, 3)

            comment_input = self._page.locator("textarea[placeholder*='comment'], div[contenteditable='true']").first
            await comment_input.click(timeout=15000)
            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))

            post_btn = self._page.get_by_role("button", name="Post").first
            await post_btn.click(timeout=15000)
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
            await msg_input.click(timeout=15000)
            await self._human_delay(0.5, 1)

            # Type with human delays
            for char in message:
                await msg_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Send the message
            send_btn = self._page.get_by_role("button", name="Send").first
            await send_btn.click(timeout=15000)
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
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Find and click the like/heart button
            like_btn = self._page.locator(
                "button[data-e2e='like-icon'], "
                "button[data-e2e='like-button'], "
                "span[data-e2e='like-icon'], "
                "button[aria-label*='Like'], "
                "button[aria-label*='like']"
            ).first
            logger.info(f"like_post: Clicking like button on {post_url}")
            await like_btn.click(timeout=15000, force=True)
            await self._human_delay(1, 2)
            logger.info(f"like_post: Like clicked successfully")
            return ActionResult(success=True, action_type="like")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"like_post FAILED on {post_url}: {e}")
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
            await unlike_btn.click(timeout=15000)
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
            await share_btn.click(timeout=15000)
            await self._human_delay(1, 2)

            # Click repost option if available
            try:
                repost_btn = self._page.get_by_role("button", name="Repost").first
                await repost_btn.click(timeout=8000)
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
            await story_btn.click(timeout=15000)
            await self._human_delay(3, 5)

            # Wait for story to play, then close
            await self._human_delay(5, 7)
            try:
                close_btn = self._page.locator(
                    "button[data-e2e='close-button'], "
                    "button[aria-label='Close']"
                ).first
                await close_btn.click(timeout=8000)
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
