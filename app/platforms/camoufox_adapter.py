import asyncio
import json
import logging
import os
import random
import re
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

            # Extract logged-in username from page source
            if logged_in:
                try:
                    import re
                    page_source = await self._page.content()
                    # Try various patterns TikTok uses
                    match = re.search(r'"uniqueId":"([^"]+)"', page_source)
                    if not match:
                        match = re.search(r'"username":"([^"]+)"', page_source)
                    if not match:
                        match = re.search(r'"user":\{"uniqueId":"([^"]+)"', page_source)
                    if match:
                        self._current_username = match.group(1).lower()
                        logger.info(f"Logged-in username: @{self._current_username}")
                except: pass

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

            # Check for blockers
            page_text = await self._extract_page_text()
            self._check_for_blockers(page_text, url)

            # PRIMARY: try clicking the Message button on the profile (most reliable,
            # TikTok keeps the button even when direct URLs return 404).
            msg_btn_clicked = False
            try:
                msg_btn_selectors = [
                    'button:has-text("Message")',
                    '[data-e2e="message-button"]',
                    'div[role="button"]:has-text("Message")',
                    '//p[text()="Send message"]',
                    '//div[contains(@class, "message")]//button',
                ]
                for sel in msg_btn_selectors:
                    try:
                        if sel.startswith('//'):
                            btn = self._page.locator(f'xpath={sel}').first
                        else:
                            btn = self._page.locator(sel).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=5000)
                            msg_btn_clicked = True
                            logger.info(f"send_dm: Clicked Message button via '{sel}'")
                            break
                    except: pass
            except Exception as e:
                logger.info(f"send_dm: Message button click attempt failed: {e}")

            if not msg_btn_clicked:
                # FALLBACK: try direct DM URLs (TikTok's URL formats have changed
                # multiple times; we try several to find one that doesn't 404).
                page_source = await self._page.content()
                uid = None
                for pattern in (r'"id"\s*:\s*"(\d{1,30})"', r'"userId"\s*:\s*"(\d{1,30})"'):
                    m = re.search(pattern, page_source)
                    if m:
                        uid = m.group(1)
                        break
                if not uid:
                    logger.warning(f"send_dm: Could not extract user_id for @{handle}")
                    return ActionResult(success=False, action_type="dm", error="Could not extract user_id")
                logger.info(f"send_dm: Got user_id={uid} for @{handle}")

                dm_urls = [
                    f"https://www.{self.platform}.com/direct/inbox?lang=en&u={uid}",
                    f"https://www.{self.platform}.com/direct/inbox?username={handle}",
                    f"https://www.{self.platform}.com/messages?u={uid}",
                ]
                for dm_url in dm_urls:
                    logger.info(f"send_dm: Trying DM URL: {dm_url}")
                    await self._page.goto(dm_url, wait_until="domcontentloaded", timeout=60000)
                    await self._human_delay(2, 3)
                    if "/404" not in self._page.url:
                        logger.info(f"send_dm: DM URL loaded (no 404)")
                        break
                    logger.warning(f"send_dm: URL 404'd, trying next format")

            await self._human_delay(2, 3)

            # Wait for DM page to load — check for chat-uniqueid or input box
            dm_loaded = False
            for attempt in range(5):
                try:
                    # Check if we landed on login page
                    if "/login" in self._page.url:
                        logger.warning("send_dm: Redirected to login page — not logged in")
                        return ActionResult(success=False, action_type="dm", error="Not logged in")

                    # Check for DM page indicator
                    chat_header = self._page.locator('p[data-e2e="chat-uniqueid"]')
                    if await chat_header.count() > 0:
                        dm_loaded = True
                        logger.info("send_dm: DM page loaded (chat-uniqueid found)")
                        break

                    # Also try finding the input directly
                    input_box = self._page.locator('div[aria-label="Send a message..."][role="textbox"]')
                    if await input_box.count() > 0:
                        dm_loaded = True
                        logger.info("send_dm: DM page loaded (input box found)")
                        break

                    await self._human_delay(2, 3)
                except:
                    await self._human_delay(2, 3)

            if not dm_loaded:
                # Check for warning/error messages
                page_text = await self._extract_page_text()
                warnings = [
                    "Only friends can send messages",
                    "privacy settings",
                    "This user is unable to receive",
                    "suspended",
                    "violated",
                    "temporarily prevented",
                    "Chat messages limit reached",
                    "You are sending messages too fast",
                    "This account can't send or receive messages",
                    "The message couldn't be sent",
                ]
                for w in warnings:
                    if w.lower() in page_text.lower():
                        logger.warning(f"send_dm: DM blocked — {w}")
                        return ActionResult(success=False, action_type="dm", error=f"DM blocked: {w}")

                # Check for DM warning element
                try:
                    warn_el = self._page.locator('div[data-e2e="dm-warning"]')
                    if await warn_el.count() > 0:
                        warn_text = await warn_el.inner_text()
                        logger.warning(f"send_dm: DM warning — {warn_text}")
                        return ActionResult(success=False, action_type="dm", error=f"DM warning: {warn_text}")
                except: pass

                try:
                    ss = await self._page.screenshot()
                    logger.warning(f"send_dm: DM page not loaded. Screenshot saved. URL: {self._page.url}")
                except: pass

                return ActionResult(success=False, action_type="dm", error="DM page not loaded")

            # Find the DM input box — exact selector from working TikTok bot
            dm_input = None
            input_selectors = [
                'div[aria-label="Send a message..."][role="textbox"]',
                'div[aria-label="Send a message"][role="textbox"]',
                'div[aria-label*="Send a message"][role="textbox"]',
                'div[data-e2e="chat-input"]',
                'div[contenteditable="true"][role="textbox"]',
            ]

            for sel in input_selectors:
                try:
                    el = self._page.locator(sel)
                    if await el.count() > 0 and await el.first.is_visible():
                        dm_input = el.first
                        logger.info(f"send_dm: Input found via '{sel}'")
                        break
                except:
                    continue

            if not dm_input:
                logger.warning("send_dm: DM input not found on loaded DM page")
                try:
                    ss = await self._page.screenshot()
                    logger.warning(f"send_dm: Screenshot saved. URL: {self._page.url}")
                except: pass
                return ActionResult(success=False, action_type="dm", error="DM input not found")

            # Clear any existing text and type message
            logger.info(f"send_dm: Typing message ({len(message)} chars)")
            await dm_input.click()
            await self._page.keyboard.press("Control+KeyA")
            await self._page.keyboard.press("Backspace")
            await self._human_delay(0.3, 0.5)

            # Paste message via clipboard
            await self._page.evaluate(f"navigator.clipboard.writeText({repr(message)})")
            await self._page.keyboard.press("Control+KeyV")
            await self._human_delay(0.5, 1)

            # Click send button — StyledSendButton class from working bot
            send_btn = self._page.locator('[class*="StyledSendButton"]').first
            try:
                if await send_btn.count() > 0:
                    await send_btn.wait_for(state="visible", timeout=5000)
                    await send_btn.click(timeout=5000)
                else:
                    # Fallback: press Enter
                    await self._page.keyboard.press("Enter")
            except:
                await self._page.keyboard.press("Enter")

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

            # Extract video owner from URL to exclude them
            video_owner = ""
            try:
                video_owner = post_url.split("/@")[-1].split("/")[0].split("?")[0].lower()
            except: pass

            # STEP 1: scope the search to the actual comment list container.
            # The previous selectors ([class*="Comment"], [class*="comment"]) were
            # too broad and matched the comment *counter* button in the action bar
            # and the logged-in user's profile link in the header, returning
            # 12 false-positive "commenters" that were all the logged-in user.
            comment_container_selectors = [
                '[data-e2e="comment-list"]',
                '[class*="CommentListContainer"]',
                '[class*="DivCommentList"]',
                '[class*="comment-list"]',
            ]
            comment_links = []
            container_found = ""
            for sel in comment_container_selectors:
                try:
                    container = self._page.locator(sel).first
                    if await container.count() > 0:
                        # Get all user profile links INSIDE the container
                        links_in_container = await container.locator('a[href*="/@"]').all()
                        if links_in_container:
                            comment_links = links_in_container
                            container_found = sel
                            break
                except: pass

            # STEP 2: if no container found, try the older per-comment-item selectors
            if not comment_links:
                item_selectors = [
                    '[class*="CommentItemContainer"] a[href*="/@"]',
                    '[class*="DivCommentContentContainer"] a[href*="/@"]',
                    '[class*="DivCommentObjectWrapper"] a[href*="/@"]',
                ]
                for sel in item_selectors:
                    try:
                        links = await self._page.query_selector_all(sel)
                        if links:
                            comment_links = links
                            container_found = sel
                            break
                    except: pass

            # STEP 3: scroll inside the container to load more comments, then re-extract
            if comment_links and container_found.startswith("["):
                try:
                    container_el = self._page.locator(container_found).first
                    prev_count = 0
                    for _ in range(15):
                        await container_el.evaluate("el => el.scrollBy(0, 800)")
                        await self._human_delay(1.0, 1.8)
                        new_links = await container_el.locator('a[href*="/@"]').all()
                        if len(new_links) == prev_count:
                            break
                        prev_count = len(new_links)
                    comment_links = await container_el.locator('a[href*="/@"]').all()
                except: pass

            # STEP 4: if we still have nothing AND a comment button exists, click it
            # (TikTok mobile/desktop sometimes loads comments in a modal)
            if not comment_links:
                for btn_sel in [
                    '[data-e2e="comment-icon"]',
                    'button[aria-label*="Comment" i]',
                    'span[data-e2e="comment-icon"]',
                ]:
                    try:
                        btn = self._page.locator(btn_sel).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=3000)
                            await self._human_delay(2, 3)
                            comment_links = await self._page.query_selector_all('a[href*="/@"]')
                            break
                    except: pass

            # STEP 5: last-resort fallback — but warn loudly because this is the
            # source of the "stuck in a loop" bug (matched header/sidebar links)
            if not comment_links:
                logger.warning(
                    f"get_post_commenters: no comment container found, "
                    f"falling back to all a[href*=/@] (may include non-commenters)"
                )
                comment_links = await self._page.query_selector_all('a[href*="/@"]')

            # Dedupe + filter
            seen = set()
            for link in comment_links[:limit * 5]:
                try:
                    href = await link.get_attribute("href")
                except: continue
                if not href or "/@" not in href:
                    continue
                username = href.split("/@")[-1].split("/")[0].split("?")[0]
                if not username or len(username) < 2:
                    continue
                if username.isdigit():
                    continue
                if username.lower() == video_owner:
                    continue
                if username in seen:
                    continue
                seen.add(username)
                results.append(UserProfile(platform_id=username, username=username))
                if len(results) >= limit:
                    break

            if results:
                logger.info(f"Extracted {len(results)} commenters from HTML (container: {container_found or 'fallback'})")
                return results

            # LLM fallback
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

            # Robust private account detection
            is_private = False

            # 1. Text-based detection (multiple variations)
            private_text_indicators = [
                "this account is private",
                "this account's posts are hidden",
                "private account",
                "account is private",
                "posts are hidden",
                "follow this account to see their photos and videos",
            ]
            text_lower = text.lower()
            for indicator in private_text_indicators:
                if indicator in text_lower:
                    is_private = True
                    logger.info(f"Private account detected (text): @{handle} — '{indicator}'")
                    break

            # 2. DOM element detection (multiple selectors)
            if not is_private:
                private_selectors = [
                    '[data-e2e="private-account"]',
                    '.private-account',
                    '[aria-label*="private" i]',
                    '[aria-label*="Private" i]',
                    'div[class*="DivPrivateAccount"]',
                    'div[class*="private"]',
                    'p[data-e2e="private-account"]',
                ]
                for sel in private_selectors:
                    try:
                        el = await self._page.query_selector(sel)
                        if el:
                            is_private = True
                            logger.info(f"Private account detected (DOM): @{handle} — selector '{sel}'")
                            break
                    except: pass

            # 3. Check if profile grid is empty (private accounts have no visible posts)
            if not is_private:
                try:
                    grid = await self._page.query_selector('[data-e2e="user-post-item"], [data-e2e="user-post-grid"]')
                    if not grid:
                        # No grid at all — could be private or empty account
                        # Check for the "follow to see" message
                        if "follow" in text_lower and ("see" in text_lower or "photos" in text_lower or "videos" in text_lower):
                            is_private = True
                            logger.info(f"Private account detected (no grid + follow text): @{handle}")
                except: pass

            # 4. Check for lock icon in profile area
            if not is_private:
                try:
                    lock_selectors = [
                        'svg[class*="lock"]',
                        'svg[class*="Lock"]',
                        '[data-e2e="lock-icon"]',
                        'span[class*="lock"]',
                    ]
                    for sel in lock_selectors:
                        el = await self._page.query_selector(sel)
                        if el:
                            is_private = True
                            logger.info(f"Private account detected (lock icon): @{handle}")
                            break
                except: pass

            # If private, skip LLM call — return minimal data
            if is_private:
                return {
                    "username": handle,
                    "bio": "",
                    "display_name": "",
                    "follower_count": "",
                    "recent_posts": [],
                    "is_private": True,
                }

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
                "is_private": False,
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

            # Try HTML extraction first — look for post links belonging to THIS user only
            posts = []
            try:
                links = await self._page.query_selector_all('a[href*="/video/"], a[href*="/photo/"]')
                seen_ids = set()
                for link in links[:limit * 5]:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    # Only include posts from this user's profile
                    if f"/@{handle}/" not in href and f"/@{handle}?" not in href:
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
        """Like a post (works for both video and photo posts)."""
        try:
            await self._ensure_browser(self._session_data)
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Try multiple selector strategies for video and photo posts
            like_btn = None
            selectors = [
                # XPath: button containing span with like icon (works for both video + photo)
                '//button[.//span[@data-e2e="browse-like-icon" or @data-e2e="like-icon"]]',
                # CSS: direct data-e2e selectors
                'button[data-e2e="like-icon"]',
                'button[data-e2e="like-button"]',
                '[data-e2e="like-icon"]',
                '[data-e2e="like-button"]',
                # Fallback: aria-label on button
                'button[aria-label*="Like"]',
                'button[aria-label*="like"]',
                # Photo/carousel viewer: like icon is an SVG inside StyledIconWrapper
                # (first StyledIconWrapper in the right action bar is the like heart)
                'div[class*="StyledIconWrapper"]:first-of-type',
                'div[class*="StyledIconWrapper"]:first-of-type svg',
                # Generic action bar button (right-side icons on photo viewer)
                '[class*="StyledActionBarButton"]:first-of-type',
            ]

            for sel in selectors:
                try:
                    if sel.startswith('//'):
                        el = self._page.locator(f'xpath={sel}').first
                    else:
                        el = self._page.locator(sel).first
                    if await el.count() > 0:
                        like_btn = el
                        logger.info(f"like_post: Found like button via '{sel}'")
                        break
                except: pass

            if not like_btn:
                # DEBUG: dump all buttons, SVGs, and interactive elements on the page
                try:
                    buttons = await self._page.query_selector_all('button')
                    logger.warning(f"like_post: No like button found. Dumping {len(buttons)} buttons on page:")
                    for i, btn in enumerate(buttons[:20]):
                        try:
                            aria = await btn.get_attribute("aria-label") or ""
                            e2e = await btn.get_attribute("data-e2e") or ""
                            cls = (await btn.get_attribute("class") or "")[:80]
                            txt = (await btn.inner_text())[:50] if await btn.is_visible() else "[hidden]"
                            logger.warning(f"  button[{i}]: aria='{aria}' e2e='{e2e}' cls='{cls}' text='{txt}'")
                        except: pass

                    # Dump all elements with data-e2e
                    e2e_els = await self._page.query_selector_all('[data-e2e]')
                    logger.warning(f"like_post: Found {len(e2e_els)} elements with data-e2e:")
                    for i, el in enumerate(e2e_els[:30]):
                        try:
                            e2e = await el.get_attribute("data-e2e") or ""
                            tag = await el.evaluate("el => el.tagName")
                            logger.warning(f"  data-e2e[{i}]: <{tag}> data-e2e='{e2e}'")
                        except: pass

                    # Dump all divs with aria-label (photo posts use divs, not buttons)
                    aria_divs = await self._page.query_selector_all('div[aria-label]')
                    logger.warning(f"like_post: Found {len(aria_divs)} divs with aria-label:")
                    for i, el in enumerate(aria_divs[:20]):
                        try:
                            aria = await el.get_attribute("aria-label") or ""
                            logger.warning(f"  div-aria[{i}]: aria-label='{aria}'")
                        except: pass

                    # Dump all SVGs inside clickable elements
                    svgs = await self._page.query_selector_all('svg')
                    logger.warning(f"like_post: Found {len(svgs)} SVGs on page")
                    for i, svg in enumerate(svgs[:15]):
                        try:
                            parent_tag = await svg.evaluate("el => el.parentElement ? el.parentElement.tagName + '.' + (el.parentElement.className || '').substring(0,50) : 'none'")
                            aria = await svg.get_attribute("aria-label") or ""
                            logger.warning(f"  svg[{i}]: parent='{parent_tag}' aria='{aria}'")
                        except: pass

                    # Also check for any element with "like" in any attribute
                    like_els = await self._page.query_selector_all('[class*="like" i], [class*="Like" i], [aria-label*="like" i], [aria-label*="Like" i]')
                    logger.warning(f"like_post: Found {len(like_els)} elements with 'like' in class/aria:")
                    for i, el in enumerate(like_els[:10]):
                        try:
                            tag = await el.evaluate("el => el.tagName")
                            cls = (await el.get_attribute("class") or "")[:80]
                            aria = await el.get_attribute("aria-label") or ""
                            logger.warning(f"  like-el[{i}]: <{tag}> cls='{cls}' aria='{aria}'")
                        except: pass

                except Exception as e:
                    logger.error(f"like_post: Debug dump failed: {e}")
                return ActionResult(success=False, action_type="like", error="Like button not found")

            # Try click, fallback to JS click
            try:
                await like_btn.click(timeout=10000, force=True)
            except Exception:
                logger.info("like_post: Regular click failed, trying JS click")
                try:
                    await like_btn.evaluate("el => el.click()")
                except Exception as e2:
                    logger.error(f"like_post: JS click also failed: {e2}")
                    return ActionResult(success=False, action_type="like", error=str(e2))

            await self._human_delay(1, 2)

            # Verify like was applied
            try:
                is_liked = await like_btn.get_attribute("aria-pressed")
                if is_liked == "true":
                    logger.info(f"like_post: Like confirmed (aria-pressed=true)")
            except: pass

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

    async def check_user_followers(self, username: str, search_names: List[str]) -> Dict[str, Any]:
        """
        Check if any of search_names appear in a user's followers list.
        Returns: {"found": bool, "matched_names": [...], "follower_count": int}
        """
        try:
            await self._ensure_browser(self._session_data)
            handle = username.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            logger.info(f"check_user_followers: Checking followers of @{handle}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Click on followers count to open followers list
            followers_clicked = False
            followers_selectors = [
                '[data-e2e="followers-count"]',
                'a[href*="/followers"]',
                'strong[title="Followers"]',
                'span:has-text("Followers")',
            ]
            for sel in followers_selectors:
                try:
                    el = self._page.locator(sel).first
                    if await el.count() > 0:
                        await el.click(timeout=10000)
                        followers_clicked = True
                        logger.info(f"check_user_followers: Clicked followers via '{sel}'")
                        await self._human_delay(2, 3)
                        break
                except: pass

            if not followers_clicked:
                logger.warning(f"check_user_followers: Could not open followers list for @{handle}")
                return {"found": False, "matched_names": [], "follower_count": 0}

            # Get total follower count
            follower_count = 0
            try:
                count_el = self._page.locator('[data-e2e="followers-count"]').first
                if await count_el.count() > 0:
                    count_text = await count_el.inner_text()
                    follower_count = self._parse_count_text(count_text)
            except: pass

            # Search through followers list for matching names
            matched = []
            search_lower = [n.lower().replace(".", " ").replace("_", " ").replace("-", " ") for n in search_names]

            # Scroll through followers list and check names
            seen = set()
            for scroll_i in range(20):  # Max 20 scrolls
                # Get all visible follower names/usernames
                try:
                    items = await self._page.query_selector_all('[data-e2e="search-user-container"], div[class*="follow-item"], div[class*="FollowerItem"]')
                    if not items:
                        # Fallback: get all links with /@
                        items = await self._page.query_selector_all('a[href*="/@"]')
                except:
                    items = []

                new_found = False
                for item in items:
                    try:
                        # Get username from link
                        link = await item.query_selector('a[href*="/@"]') if await item.evaluate("el => el.tagName") != "A" else item
                        if not link:
                            continue
                        href = await link.get_attribute("href")
                        if not href or "/@" not in href:
                            continue
                        item_username = href.split("/@")[1].split("?")[0].split("/").lower()
                        if item_username in seen:
                            continue
                        seen.add(item_username)
                        new_found = True

                        # Get display name
                        display_name = ""
                        try:
                            name_el = await item.query_selector('p[class*="nickname"], span[class*="nickname"], h3, h4')
                            if name_el:
                                display_name = (await name_el.inner_text()).lower()
                        except: pass

                        # Check if this follower matches any of our search names
                        combined = f"{item_username} {display_name}".replace(".", " ").replace("_", " ").replace("-", " ")
                        for search_name in search_lower:
                            # Check if search name words appear in the follower's name
                            search_words = search_name.split()
                            if len(search_words) >= 2:
                                # Multi-word name: check if most words match
                                matches = sum(1 for w in search_words if w in combined)
                                if matches >= len(search_words) - 1:  # Allow 1 word mismatch
                                    matched.append({"username": item_username, "display_name": display_name, "matched_search": search_name})
                                    logger.info(f"check_user_followers: FOUND match '@{item_username}' ({display_name}) for '{search_name}'")
                            else:
                                # Single word: exact or substring match
                                if search_words[0] in combined and len(search_words[0]) >= 3:
                                    matched.append({"username": item_username, "display_name": display_name, "matched_search": search_name})
                                    logger.info(f"check_user_followers: FOUND match '@{item_username}' ({display_name}) for '{search_name}'")
                    except: pass

                # If we found matches, stop early
                if matched:
                    break

                # If no new items found, we've reached the end
                if not new_found and scroll_i > 2:
                    break

                # Scroll down
                try:
                    await self._page.mouse.wheel(0, 800)
                    await self._human_delay(1, 2)
                except: pass

            logger.info(f"check_user_followers: @{handle} has {follower_count} followers, found {len(matched)} matches")
            return {
                "found": len(matched) > 0,
                "matched_names": matched,
                "follower_count": follower_count
            }
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"check_user_followers failed: {e}")
            return {"found": False, "matched_names": [], "follower_count": 0}

    async def get_target_followers(self, username: str, max_scroll: int = 50) -> set:
        """
        Scrape a user's followers list into a set for O(1) lookups.
        Returns a set of lowercase usernames.
        """
        followers = set()
        try:
            await self._ensure_browser(self._session_data)
            handle = username.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            logger.info(f"get_target_followers: Scraping followers of @{handle}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Click followers count
            followers_selectors = [
                '[data-e2e="followers-count"]',
                'a[href*="/followers"]',
                'strong[title="Followers"]',
            ]
            for sel in followers_selectors:
                try:
                    el = self._page.locator(sel).first
                    if await el.count() > 0:
                        await el.click(timeout=10000)
                        logger.info(f"get_target_followers: Clicked followers via '{sel}'")
                        await self._human_delay(2, 3)
                        break
                except: pass

            # Infinite scroll and collect usernames
            prev_count = 0
            for i in range(max_scroll):
                # Extract all visible follower links
                links = await self._page.query_selector_all('a[href*="/@"]')
                for link in links:
                    try:
                        href = await link.get_attribute("href")
                        if href and "/@" in href:
                            uname = href.split("/@")[-1].split("/")[0].split("?")[0].lower()
                            if uname and len(uname) > 1 and not uname.isdigit():
                                followers.add(uname)
                    except: pass

                if len(followers) == prev_count and i > 3:
                    break
                prev_count = len(followers)

                # Scroll down
                try:
                    await self._page.mouse.wheel(0, 800)
                    await self._human_delay(1, 2)
                except: pass

            logger.info(f"get_target_followers: Collected {len(followers)} follower usernames for @{handle}")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"get_target_followers failed for @{handle}: {e}")
        return followers

    def _parse_count_text(self, text: str) -> int:
        """Parse follower count text like '1.2K' or '12,345'."""
        if not text:
            return 0
        text = text.replace(",", "").replace(" ", "").lower()
        if text.endswith("k"):
            try: return int(float(text[:-1]) * 1000)
            except: return 0
        elif text.endswith("m"):
            try: return int(float(text[:-1]) * 1000000)
            except: return 0
        try:
            return int(text)
        except:
            return 0

    async def search_for_clones(self, target_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search TikTok for accounts similar to target_name. Returns list of {username, display_name, bio, followers}."""
        try:
            await self._ensure_browser(self._session_data)
            # Clean the name for search (remove dots, underscores, etc.)
            clean_name = target_name.replace(".", " ").replace("_", " ").replace("-", " ").strip()
            search_url = f"https://www.{self.platform}.com/search/user?q={clean_name}&lang=en"
            logger.info(f"search_for_clones: Searching for '{clean_name}'")
            await self._page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            # Scroll to load more results
            for _ in range(3):
                await self._page.mouse.wheel(0, 1000)
                await self._human_delay(1, 2)

            # Extract user cards from search results
            results = []
            try:
                # TikTok search user cards
                cards = await self._page.query_selector_all('[data-e2e="search-user-container"], div[class*="user-card"], div[class*="UserCard"]')
                if not cards:
                    # Fallback: look for any user links
                    cards = await self._page.query_selector_all('a[href*="/@"]')

                seen_usernames = set()
                for card in cards[:limit * 2]:
                    try:
                        # Get username
                        link = await card.query_selector('a[href*="/@"]') if await card.evaluate("el => el.tagName") != "A" else card
                        if not link:
                            continue
                        href = await link.get_attribute("href")
                        if not href or "/@" not in href:
                            continue
                        username = href.split("/@")[1].split("?")[0].split("/")[0]
                        if username in seen_usernames or not username:
                            continue
                        seen_usernames.add(username)

                        # Get display name and bio
                        display_name = ""
                        bio = ""
                        try:
                            name_el = await card.query_selector('p[class*="nickname"], span[class*="nickname"], h3, h4')
                            if name_el:
                                display_name = await name_el.inner_text()
                        except: pass
                        try:
                            bio_el = await card.query_selector('p[class*="desc"], span[class*="bio"], p[class*="account"]')
                            if bio_el:
                                bio = await bio_el.inner_text()
                        except: pass

                        results.append({
                            "username": username,
                            "display_name": display_name,
                            "bio": bio,
                        })
                    except: pass

            except Exception as e:
                logger.warning(f"search_for_clones: Error extracting cards: {e}")

            # If HTML extraction failed, use LLM
            if not results:
                try:
                    text = await self._extract_page_text()
                    llm_response = self._llm_decide(
                        text,
                        f"Extract the first {limit} user profiles from this search result. Return JSON: {{\"users\": [{{\"username\": \"...\", \"display_name\": \"...\", \"bio\": \"...\"}}]}}"
                    )
                    import json
                    data = json.loads(llm_response)
                    results = data.get("users", [])[:limit]
                except: pass

            logger.info(f"search_for_clones: Found {len(results)} accounts for '{clean_name}'")
            return results
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"search_for_clones failed: {e}")
            return []

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
        self._current_username: Optional[str] = None
