import asyncio
import json
import logging
import os
import random
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Page, BrowserContext

from app.platforms.base import PlatformAdapter, UserProfile, ActionResult
from app.exceptions import BlockerDetected

logger = logging.getLogger("FacebookCamoufoxAdapter")

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
    "confirm your identity", "review your account",
    "content not available",
]


def _get_provider_manager():
    from app.llm.provider_manager import get_provider_manager
    return get_provider_manager()


class FacebookCamoufoxAdapter(PlatformAdapter):
    """Anti-detection adapter for Facebook using Camoufox (patched Firefox) + Playwright."""

    platform_name: str = "facebook"

    def __init__(self, platform: str = "facebook", **kwargs):
        self.platform = "facebook"
        self.platform_name = "facebook"
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._session_data: Optional[str] = None
        self._camoufox = None

    # ── Browser lifecycle ────────────────────────────────────────────────

    async def _ensure_browser(self, session_data: Optional[str] = None):
        if self._page and not self._page.is_closed():
            return

        self._session_data = session_data
        proxy_config = self._get_proxy_config()

        from camoufox.async_api import AsyncCamoufox

        launch_kwargs = {
            "headless": True,
            "os": ["windows", "macos"],
        }

        logger.info("Launching Camoufox browser for facebook...")
        self._camoufox = AsyncCamoufox(**launch_kwargs)
        try:
            self._context = await self._camoufox.__aenter__()
        except Exception as e:
            logger.warning(f"Camoufox launch failed, retrying without proxy: {e}")
            self._camoufox = AsyncCamoufox(headless=True, os=["windows", "macos"])
            self._context = await self._camoufox.__aenter__()

        if hasattr(self._context, "new_context"):
            self._context = await self._context.new_context()

        if session_data:
            await self._load_cookies(session_data)

        self._page = await self._context.new_page()
        logger.info("Camoufox browser ready for facebook")

    async def _load_cookies(self, session_data: str):
        try:
            cookies = json.loads(session_data)
            if isinstance(cookies, list) and cookies:
                await self._context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    async def _get_cookies(self) -> str:
        try:
            cookies = await self._context.cookies()
            return json.dumps(cookies)
        except Exception:
            return "[]"

    async def _run_with_retry(self, fn, *args, **kwargs):
        for attempt in range(2):
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
                if is_browser_dead and attempt == 0:
                    logger.warning(f"Browser died, restarting: {e}")
                    self._page = None
                    self._context = None
                    await self._ensure_browser(self._session_data)
                    continue
                raise

    @staticmethod
    def _get_proxy_config() -> Optional[dict]:
        url = os.getenv("SKYVERN_PROXY_URL", "").strip()
        if not url:
            return None
        if not url.startswith(("http://", "https://", "socks5://")):
            url = f"http://{url}"
        username = os.getenv("SKYVERN_PROXY_USERNAME", "").strip()
        password = os.getenv("SKYVERN_PROXY_PASSWORD", "").strip()
        config = {"url": url}
        if username:
            config["username"] = username
            config["password"] = password
        return config

    # ── Human-like helpers ───────────────────────────────────────────────

    def _check_for_blockers(self, text: str, url: str = ""):
        lower = text.lower()
        for signal in BLOCKER_SIGNALS:
            if signal in lower:
                raise BlockerDetected(
                    blocker_type=signal.replace(" ", "_"),
                    message=f"Detected '{signal}' on page. Human intervention required.",
                    url=url,
                )

    async def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def _human_scroll(self):
        for _ in range(random.randint(1, 3)):
            amount = random.randint(100, 400)
            direction = 1 if random.random() > 0.3 else -1
            await self._page.mouse.wheel(0, amount * direction)
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def _human_move_mouse(self):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await self._page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.3, 0.7))

    async def _navigate(self, url: str):
        async def _do_navigate():
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)
            await self._human_scroll()
            await self._human_move_mouse()
        await self._run_with_retry(_do_navigate)

    async def _extract_page_text(self) -> str:
        async def _do_extract():
            try:
                return await self._page.inner_text("body")
            except Exception:
                return ""
        return await self._run_with_retry(_do_extract)

    def _llm_decide(self, page_text: str, prompt: str) -> str:
        pm = _get_provider_manager()
        provider = pm.get_next_provider()
        if not provider:
            return ""

        full_prompt = (
            f"You are looking at a Facebook page.\n"
            f"Page text (first 2000 chars): {page_text[:2000]}\n\n"
            f"Task: {prompt}\n\n"
            f"Respond with a JSON object describing what to do. "
            f'For example: {{"action": "click", "selector": "button Follow"}} or '
            f'{{"action": "type", "selector": "input[name=username]", "text": "hello"}} or '
            f'{{"action": "extract", "data": {{...}}}}'
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
                timeout=90,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return ""

    # ── Facebook URL helpers ─────────────────────────────────────────────

    @staticmethod
    def _profile_url(user_id: str) -> str:
        """Build a Facebook profile URL, handling vanity vs numeric IDs."""
        uid = user_id.lstrip("@")
        if uid.isdigit():
            return f"https://www.facebook.com/profile.php?id={uid}"
        return f"https://www.facebook.com/{uid}"

    @staticmethod
    def _dm_url(user_id: str) -> str:
        uid = user_id.lstrip("@")
        if uid.isdigit():
            return f"https://www.facebook.com/messages/t/{uid}"
        return f"https://www.facebook.com/messages/t/{uid}"

    @staticmethod
    def _group_url(group_id: str) -> str:
        gid = group_id.lstrip("/")
        if gid.startswith("https://"):
            return gid
        return f"https://www.facebook.com/groups/{gid}"

    # ── PlatformAdapter implementation ───────────────────────────────────

    async def authenticate(
        self,
        session_data: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        try:
            await self._ensure_browser(session_data)
            await self._navigate("https://www.facebook.com/")
            text = await self._extract_page_text()
            self._check_for_blockers(text, "https://www.facebook.com/")

            # If credentials provided and not logged in, try to log in
            logged_in = not any(w in text.lower() for w in ["log in", "sign in", "sign up"])
            if not logged_in and username and password:
                logged_in = await self._login_with_credentials(username, password)

            logger.info(f"Auth check: logged_in={logged_in}")
            return logged_in
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def _login_with_credentials(self, username: str, password: str) -> bool:
        """Attempt to log in with email/password on facebook.com/login."""
        try:
            await self._navigate("https://www.facebook.com/login")
            await self._human_delay(2, 3)

            # Fill email
            email_input = self._page.locator(
                'input[name="email"], input#email, input[placeholder*="Email"], input[placeholder*="Phone"]'
            ).first
            await email_input.click(timeout=5000)
            await email_input.fill(username)
            await self._human_delay(0.5, 1)

            # Fill password
            pass_input = self._page.locator(
                'input[name="pass"], input#pass, input[type="password"]'
            ).first
            await pass_input.click(timeout=5000)
            await pass_input.fill(password)
            await self._human_delay(0.5, 1)

            # Click log in
            login_btn = self._page.locator(
                'button[name="login"], button[type="submit"], input[type="submit"]'
            ).first
            await login_btn.click(timeout=5000)
            await self._human_delay(3, 5)

            text = await self._extract_page_text()
            return not any(w in text.lower() for w in ["log in", "sign in", "sign up"])
        except Exception as e:
            logger.error(f"Login with credentials failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = f"https://www.facebook.com/search/people/?q={query}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Scroll to load more results
            for _ in range(5):
                await self._page.mouse.wheel(0, 800)
                await self._human_delay(1.5, 2.5)

            text = await self._extract_page_text()

            # Try HTML extraction first
            usernames = []
            try:
                links = await self._page.locator('a[role="link"]').all()
                seen = set()
                for link in links[:limit * 3]:
                    href = await link.get_attribute("href")
                    if not href or "/groups/" in href or "/events/" in href:
                        continue
                    import re
                    if "profile.php" in href:
                        match = re.search(r"id=(\d+)", href)
                        if match:
                            uid = match.group(1)
                            if uid not in seen:
                                seen.add(uid)
                                usernames.append(uid)
                    elif "facebook.com/" in href:
                        parts = href.split("facebook.com/")
                        if len(parts) > 1:
                            uname = parts[1].split("/")[0].split("?")[0]
                            skip = {"watch", "marketplace", "groups", "gaming", "reel", "stories"}
                            if uname and uname not in seen and uname not in skip:
                                seen.add(uname)
                                usernames.append(uname)
                    if len(usernames) >= limit:
                        break
            except Exception as e:
                logger.warning(f"HTML extraction failed: {e}")

            if usernames:
                for u in usernames[:limit]:
                    results.append(UserProfile(platform_id=u, username=u))
                logger.info(f"Extracted {len(results)} users from HTML")
            else:
                llm_response = self._llm_decide(
                    text,
                    f"Extract the first {limit} user profiles from this Facebook search page. "
                    f'Return JSON: {{"users": [{{"username": "...", "display_name": "..."}}]}}'
                )
                try:
                    data = json.loads(llm_response)
                    for item in data.get("users", [])[:limit]:
                        results.append(UserProfile(
                            platform_id=item.get("username", ""),
                            username=item.get("username", ""),
                            display_name=item.get("display_name"),
                        ))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("LLM extraction also failed")

        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Search users failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Facebook doesn't expose followers easily; try LLM extraction
            llm_response = self._llm_decide(
                text,
                f"Extract follower names/usernames from this Facebook profile page (if visible). "
                f'Return JSON: {{"users": [{{"username": "...", "display_name": "..."}}]}}'
            )
            try:
                data = json.loads(llm_response)
                for item in data.get("users", [])[:limit]:
                    results.append(UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    ))
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM extraction failed for followers")

        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get followers failed: {e}")
        return results

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Try "Add Friend" first
            add_friend_btn = self._page.get_by_role("button", name="Add Friend").first
            try:
                await add_friend_btn.click(timeout=5000)
                await self._human_delay(1, 2)
                return ActionResult(success=True, action_type="add_friend")
            except Exception:
                pass

            # Try "Follow"
            follow_btn = self._page.get_by_role("button", name="Follow").first
            try:
                await follow_btn.click(timeout=5000)
                await self._human_delay(1, 2)
                return ActionResult(success=True, action_type="follow")
            except Exception:
                pass

            # Fallback: LLM
            llm_response = self._llm_decide(
                text,
                "Find and click the Add Friend or Follow button on this profile. "
                'Return JSON: {{"action": "click", "target": "Add Friend" or "Follow"}}'
            )
            if llm_response:
                try:
                    data = json.loads(llm_response)
                    target = data.get("target", "")
                    if target:
                        btn = self._page.get_by_role("button", name=target).first
                        await btn.click(timeout=5000)
                        await self._human_delay(1, 2)
                        return ActionResult(success=True, action_type=target.lower().replace(" ", "_"))
                except Exception:
                    pass

            return ActionResult(success=False, action_type="follow", error="Button not found")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Try "Following" / "Friends" button to unfriend/unfollow
            for btn_name in ["Following", "Friends", "Friend"]:
                btn = self._page.get_by_role("button", name=btn_name).first
                try:
                    await btn.click(timeout=5000)
                    await self._human_delay(1, 2)
                    # Confirm unfriend/unfollow if dialog appears
                    confirm = self._page.get_by_role("button", name="Unfriend").first
                    try:
                        await confirm.click(timeout=3000)
                        await self._human_delay(1, 2)
                    except Exception:
                        pass
                    return ActionResult(success=True, action_type="unfollow")
                except Exception:
                    continue

            return ActionResult(success=False, action_type="unfollow", error="Button not found")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._dm_url(user_id)
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Messenger input
            msg_input = self._page.locator(
                '[role="textbox"][aria-label*="Message"], '
                '[role="textbox"][aria-label*="message"], '
                'div[contenteditable="true"][data-testid="message-input"], '
                'div[contenteditable="true"]'
            ).first
            await msg_input.click(timeout=5000)
            await self._human_delay(0.5, 1)

            for char in message:
                await msg_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Press Enter to send
            await msg_input.press("Enter")
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="dm")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"send_dm failed for {user_id}: {e}")
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def check_inbox(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate("https://www.facebook.com/messages/")
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            llm_response = self._llm_decide(
                text,
                f"Extract up to {limit} unread conversations from this Messenger inbox. "
                f'Return JSON: {{"unread_conversations": [{{"username": "...", "latest_message": "...", "unread_count": 1}}]}}'
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
            await self._navigate(self._dm_url(user_id))
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            llm_response = self._llm_decide(
                text,
                f"Extract the last {limit} messages from this conversation. "
                f'Return JSON: {{"messages": [{{"sender": "me" or "{user_id}", "content": "..."}}]}}'
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
            url = self._group_url(group_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Scroll to load members
            for _ in range(5):
                await self._page.mouse.wheel(0, 1000)
                await self._human_delay(1.5, 2.5)

            text = await self._extract_page_text()

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} group members. "
                f'Return JSON: {{"users": [{{"username": "...", "display_name": "..."}}]}}'
            )
            try:
                data = json.loads(llm_response)
                for item in data.get("users", [])[:limit]:
                    results.append(UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    ))
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM extraction failed for group members")

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

            # Scroll to load comments
            for _ in range(3):
                await self._page.mouse.wheel(0, 600)
                await self._human_delay(1.5, 2)

            text = await self._extract_page_text()

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} users who commented on this post. "
                f'Return JSON: {{"users": [{{"username": "...", "display_name": "..."}}]}}'
            )
            try:
                data = json.loads(llm_response)
                for item in data.get("users", [])[:limit]:
                    results.append(UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    ))
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM extraction failed for commenters")

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

            for _ in range(3):
                await self._page.mouse.wheel(0, 600)
                await self._human_delay(1.5, 2)

            text = await self._extract_page_text()

            llm_response = self._llm_decide(
                text,
                f"Extract the first {limit} comments with author and text. "
                f'Return JSON: {{"comments": [{{"author": "...", "text": "..."}}]}}'
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
                f"Find the comment by '{comment_id}' and reply with '{message}'. "
                f'Return JSON: {{"action": "click_reply", "target": "..."}}'
            )
            return ActionResult(success=True, action_type="reply_comment")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="reply_comment", error=str(e))

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        uid = user_id.lstrip("@")
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(uid)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            llm_response = self._llm_decide(
                text,
                "Extract profile info: bio, display name, follower/friend count. "
                'Return JSON: {{"bio": "...", "display_name": "...", "follower_count": "...", "friend_count": "..."}}'
            )
            try:
                data = json.loads(llm_response)
            except (json.JSONDecodeError, TypeError):
                data = {}

            return {
                "username": uid,
                "bio": data.get("bio", ""),
                "display_name": data.get("display_name", ""),
                "follower_count": data.get("follower_count", ""),
                "friend_count": data.get("friend_count", ""),
            }
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"username": uid, "bio": "", "display_name": "", "follower_count": "", "friend_count": ""}

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            for _ in range(3):
                await self._page.mouse.wheel(0, 800)
                await self._human_delay(1.5, 2)

            text = await self._extract_page_text()

            llm_response = self._llm_decide(
                text,
                f"Extract the {limit} most recent posts with URLs and captions. "
                f'Return JSON: {{"posts": [{{"url": "...", "caption": "..."}}]}}'
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
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            # Facebook comment input
            comment_input = self._page.locator(
                '[aria-label*="Write a comment"], '
                '[aria-label*="comment as"], '
                'div[contenteditable="true"][role="textbox"]'
            ).first
            await comment_input.click(timeout=5000)
            await self._human_delay(0.5, 1)

            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            # Press Enter to submit comment
            await comment_input.press("Enter")
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="comment")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Click first post
            first_post = self._page.locator(
                'div[role="article"], '
                'div[data-ad-rendering-role="story_message"], '
                'a[href*="/posts/"], a[href*="/photos/"], a[href*="/videos/"]'
            ).first
            await first_post.click(timeout=5000)
            await self._human_delay(2, 3)

            comment_input = self._page.locator(
                '[aria-label*="Write a comment"], '
                'div[contenteditable="true"][role="textbox"]'
            ).first
            await comment_input.click(timeout=5000)
            await self._human_delay(0.5, 1)

            for char in message:
                await comment_input.type(char, delay=random.randint(50, 150))
            await comment_input.press("Enter")
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
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(self._dm_url(user_id))
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            msg_input = self._page.locator(
                '[role="textbox"][aria-label*="Message"], '
                'div[contenteditable="true"]'
            ).first
            await msg_input.click(timeout=5000)
            await self._human_delay(0.5, 1)

            for char in message:
                await msg_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)
            await msg_input.press("Enter")
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="reply_dm")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="reply_dm", error=str(e))

    async def like_post(self, post_url: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            # Facebook like button uses aria-label "Like" or data-testid
            like_btn = self._page.locator(
                'div[aria-label="Like"][role="button"], '
                'div[aria-label="like"][role="button"], '
                '[data-testid="ufi_like"], '
                'button[aria-label*="Like"]'
            ).first
            await like_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="like")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="like", error=str(e))

    async def unlike_post(self, post_url: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            unlike_btn = self._page.locator(
                'div[aria-label="Unlike"][role="button"], '
                'div[aria-label="unlike"][role="button"], '
                '[data-testid="ufi_like"], '
                'button[aria-label*="Unlike"]'
            ).first
            await unlike_btn.click(timeout=5000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="unlike")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="unlike", error=str(e))

    async def share_post(self, post_url: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            share_btn = self._page.locator(
                'div[aria-label="Share"][role="button"], '
                'div[aria-label="share"][role="button"], '
                'button[aria-label*="Share"]'
            ).first
            await share_btn.click(timeout=5000)
            await self._human_delay(1, 2)

            # Click "Share now" if dialog appears
            try:
                share_now = self._page.get_by_role("button", name="Share now").first
                await share_now.click(timeout=3000)
                await self._human_delay(1, 2)
            except Exception:
                pass

            return ActionResult(success=True, action_type="share")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="share", error=str(e))

    async def view_stories(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            # Facebook stories are shown as circular avatars at the top
            story_btn = self._page.locator(
                'div[aria-label*="Story"], '
                'a[href*="/stories/"]'
            ).first
            await story_btn.click(timeout=5000)
            await self._human_delay(5, 7)

            # Close the story viewer
            try:
                close_btn = self._page.locator(
                    'div[aria-label="Close"], '
                    'button[aria-label="Close"]'
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
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            is_live = "live" in text.lower() and (
                "watch" in text.lower() or "streaming" in text.lower() or "LIVE" in text
            )
            return {"username": user_id, "is_live": is_live, "url": url}
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Check live failed: {e}")
            return {"username": user_id, "is_live": False, "url": ""}

    async def close(self):
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
