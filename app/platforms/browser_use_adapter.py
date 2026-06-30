"""
Browser Use adapter — replaces SkyvernAdapter for all non-Camoufox platforms.

Uses Browser Use (https://github.com/browser-use/browser-use) for AI-powered
browser automation with self-healing, caching, and structured extraction.
Faster and cheaper than Skyvern's vision-based approach.
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Optional, List, Dict, Any

from app.platforms.base import PlatformAdapter, UserProfile, ActionResult
from app.exceptions import BlockerDetected

logger = logging.getLogger("BrowserUseAdapter")

# ── Blocker signals (shared with Skyvern adapter) ────────────
BLOCKER_SIGNALS = [
    "login page", "log in", "sign in", "sign up",
    "create an account", "create account",
    "phone number", "email verification",
    "two-factor", "2fa", "otp",
    "welcome back", "enter your password",
    "captcha", "verify you are human", "verification required",
    "robot check", "bot check", "security check",
    "prove you", "not a robot", "human verification",
    "please verify", "verify your identity",
    "turnstile", "recaptcha", "hcaptcha", "funcaptcha",
    "access denied", "blocked", "suspended",
    "banned", "deactivated", "restricted",
    "account disabled", "account suspended",
    "temporarily locked", "temporarily blocked",
    "too many attempts", "rate limit",
    "try again later", "slow down",
    "sorry, this page isn't available", "page not found",
    "this account is private", "this user is private",
    "confirm it's you", "suspicious activity",
    "something went wrong", "unusual activity",
    "suspicious login", "account locked",
    "verify your account", "login required",
    "sign in to continue", "this content is unavailable",
    "content not available", "log in to continue",
    "cloudflare", "checking your browser",
    "attention required", "just a moment",
    "browser verification", "challenge",
]

# Platform URL templates
PROFILE_URLS = {
    "instagram": "https://www.instagram.com/{handle}/",
    "twitter": "https://x.com/{handle}",
    "facebook": "https://www.facebook.com/{handle}",
    "linkedin": "https://www.linkedin.com/in/{handle}/",
    "tiktok": "https://www.tiktok.com/@{handle}",
    "substack": "https://substack.com/@{handle}",
    "gmail": "https://accounts.google.com/signin",
}

SEARCH_URLS = {
    "instagram": "https://www.instagram.com/explore/search/?q={query}",
    "twitter": "https://x.com/search?q={query}&type=users",
    "facebook": "https://www.facebook.com/search/people/?q={query}",
    "linkedin": "https://www.linkedin.com/search/results/people/?keywords={query}",
    "tiktok": "https://www.tiktok.com/search/user?q={query}",
    "substack": "https://substack.com/search?q={query}",
}

DM_URLS = {
    "instagram": "https://www.instagram.com/direct/t/{uid}",
    "twitter": "https://x.com/messages/compose?recipient_id={uid}",
    "facebook": "https://www.facebook.com/messages/t/{uid}",
    "linkedin": "https://www.linkedin.com/messaging/thread/{uid}",
    "tiktok": "https://www.tiktok.com/messages?lang=en&u={uid}",
}


def _get_provider_manager():
    from app.llm.provider_manager import get_provider_manager
    return get_provider_manager()


def _get_llm():
    """Create a langchain chat model from the current provider."""
    pm = _get_provider_manager()
    provider = pm.get_next_provider()
    if not provider:
        logger.warning("No LLM provider available, using default")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini")

    cfg = provider.config
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=0.1,
    )


class BrowserUseAdapter(PlatformAdapter):
    """AI-powered adapter using Browser Use for all platforms."""

    platform_name: str = "browser_use"

    def __init__(self, platform: str, **kwargs):
        self.platform = platform.lower()
        self.platform_name = platform.lower()
        self._browser = None
        self._context = None
        self._page = None
        self._cookies_loaded = False
        self._current_username: Optional[str] = None

    # ── Browser lifecycle ──────────────────────────────────────

    async def _ensure_browser(self, session_data: Optional[str] = None):
        """Launch Browser Use browser and load cookies."""
        if self._browser and self._page and not self._page.is_closed():
            if session_data and not self._cookies_loaded:
                await self._load_cookies(session_data)
            return

        from browser_use import Browser, BrowserProfile

        proxy_url = os.getenv("SKYVERN_PROXY_URL", "").strip()
        proxy_config = {"server": proxy_url} if proxy_url else None

        profile = BrowserProfile(
            headless=True,
            disable_security=True,
            extra_chromium_args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            proxy=proxy_config,
        )

        self._browser = Browser(profile=profile)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        # Set stealth headers
        await self._page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
        })

        if session_data:
            await self._load_cookies(session_data)

        logger.info(f"Browser launched for {self.platform}")

    async def _load_cookies(self, session_data: str):
        """Load cookies from session_data JSON into the browser context."""
        try:
            cookies = json.loads(session_data)
            if not isinstance(cookies, list):
                return
            playwright_cookies = []
            for c in cookies:
                cookie = {
                    "name": c.get("name", ""),
                    "value": c.get("value", ""),
                    "domain": c.get("domain", ""),
                    "path": c.get("path", "/"),
                }
                if cookie["name"] and cookie["value"] and cookie["domain"]:
                    playwright_cookies.append(cookie)
            if playwright_cookies:
                await self._context.add_cookies(playwright_cookies)
                self._cookies_loaded = True
                logger.info(f"Loaded {len(playwright_cookies)} cookies for {self.platform}")
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")

    async def close(self):
        """Clean up browser resources."""
        try:
            if self._browser:
                await self._browser.close()
                logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self._browser = None
            self._context = None
            self._page = None

    # ── Human-like behavior ────────────────────────────────────

    async def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _human_scroll(self):
        for _ in range(random.randint(1, 3)):
            await self._page.mouse.wheel(0, random.randint(100, 400))
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def _human_type(self, selector: str, text: str):
        """Type text character by character with human-like delays."""
        await self._page.click(selector)
        for char in text:
            await self._page.keyboard.type(char, delay=random.randint(30, 120))
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _dismiss_overlay(self):
        """Try to dismiss common overlays/popups."""
        dismiss_selectors = [
            '[data-testid="sheetDialog"] [aria-label="Close"]',
            'button:has-text("Not Now")',
            'button:has-text("No thanks")',
            'button:has-text("Dismiss")',
            'button:has-text("Close")',
            'button:has-text("Cancel")',
            '[aria-label="Close"]',
            '.modal-close',
        ]
        for sel in dismiss_selectors:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await self._human_delay(0.5, 1.0)
            except:
                pass

    # ── Blocker detection ──────────────────────────────────────

    def _check_for_blockers(self, text: str, url: str = ""):
        """Check page text for blocker signals. Raises BlockerDetected."""
        lower = text.lower()
        for signal in BLOCKER_SIGNALS:
            if signal in lower:
                logger.warning(f"Blocker detected: '{signal}' on {url}")
                raise BlockerDetected(
                    blocker_type=signal.replace(" ", "_"),
                    message=f"Detected '{signal}' on page. Human intervention required.",
                    url=url,
                )

    async def _check_page_for_blockers(self):
        """Read page text and check for blockers."""
        try:
            text = await self._page.inner_text("body")
            self._check_for_blockers(text, self._page.url())
        except BlockerDetected:
            raise
        except:
            pass

    # ── AI extraction via Browser Use Agent ────────────────────

    async def _extract_with_ai(self, task: str, url: Optional[str] = None, schema: Optional[dict] = None) -> dict:
        """Use Browser Use Agent for complex extraction tasks."""
        from browser_use import Agent, BrowserProfile

        llm = _get_llm()

        if schema:
            schema_str = json.dumps(schema, indent=2)
            task = f"{task}\n\nReturn data as JSON matching this schema:\n{schema_str}"

        agent = Agent(
            task=task,
            llm=llm,
            browser_profile=BrowserProfile(
                headless=True,
                disable_security=True,
            ),
        )

        try:
            history = await agent.run()
            result = history.final_result() if history else ""

            if result:
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"raw": result}
            return {}
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return {}

    # ── PlatformAdapter interface ──────────────────────────────

    async def authenticate(
        self,
        session_data: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        try:
            await self._ensure_browser(session_data)
            self._current_username = username

            home_url = f"https://www.{self.platform}.com"
            await self._page.goto(home_url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)

            # Check for login indicators
            text = await self._page.inner_text("body")
            login_indicators = ["log in", "sign in", "login", "sign up"]
            is_logged_out = any(ind in text.lower() for ind in login_indicators)

            if is_logged_out and not session_data:
                logger.warning(f"Not logged in to {self.platform} and no session data")
                return False

            logger.info(f"Authenticated to {self.platform}")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            url_template = SEARCH_URLS.get(self.platform, f"https://www.{self.platform}.search?q={{query}}")
            url = url_template.format(query=query)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)
            await self._human_scroll()

            task = (
                f"Extract the first {limit} user profiles from this search results page. "
                f"For each user, return their username and display name."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "display_name": {"type": "string"},
                            },
                        },
                    }
                },
            })

            for item in data.get("users", [])[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except Exception as e:
            logger.error(f"Search users failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            handle = user_id.lstrip("@")
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)

            # Try to click followers link/button
            followers_selectors = [
                'a:has-text("followers")',
                'a[href*="followers"]',
                '[data-testid="followers"]',
                'a:has-text("Followers")',
            ]
            for sel in followers_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el:
                        await el.click()
                        await self._human_delay(2, 3)
                        break
                except:
                    continue

            task = (
                f"Extract the first {limit} followers from this followers list. "
                f"For each user, return their username and display name."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "display_name": {"type": "string"},
                            },
                        },
                    }
                },
            })

            for item in data.get("users", [])[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except Exception as e:
            logger.error(f"Get followers failed: {e}")
        return results

    async def follow(self, user_id: str) -> ActionResult:
        try:
            handle = user_id.lstrip("@")
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)
            await self._check_page_for_blockers()

            follow_selectors = [
                'button:has-text("Follow")',
                'button:has-text("Follow")',
                '[data-testid$="-follow"]',
                'button[aria-label*="Follow"]',
                'button:has-text("Connect")',
                'button:has-text("Subscribe")',
            ]
            for sel in follow_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        text = await el.inner_text()
                        if "following" not in text.lower() and "unfollow" not in text.lower():
                            await el.click()
                            await self._human_delay(1, 2)
                            logger.info(f"Followed @{handle}")
                            return ActionResult(success=True, action_type="follow")
                except:
                    continue

            return ActionResult(success=False, action_type="follow", error="Follow button not found")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            handle = user_id.lstrip("@")
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)

            unfollow_selectors = [
                'button:has-text("Following")',
                'button:has-text("Unfollow")',
                '[data-testid$="-unfollow"]',
                'button[aria-label*="Unfollow"]',
            ]
            for sel in unfollow_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await self._human_delay(0.5, 1)
                        # Confirm unfollow if dialog appears
                        confirm = await self._page.query_selector('button:has-text("Unfollow")')
                        if confirm:
                            await confirm.click()
                        logger.info(f"Unfollowed @{handle}")
                        return ActionResult(success=True, action_type="unfollow")
                except:
                    continue

            return ActionResult(success=False, action_type="unfollow", error="Unfollow button not found")
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            handle = user_id.lstrip("@")
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)
            await self._check_page_for_blockers()

            # Click message/DM button
            dm_selectors = [
                'a:has-text("Message")',
                'button:has-text("Message")',
                '[data-testid="sendDMFromProfile"]',
                'a[href*="/direct/"]',
                'button:has-text("Send message")',
                'a:has-text("Send message")',
            ]
            clicked = False
            for sel in dm_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        clicked = True
                        await self._human_delay(1, 2)
                        break
                except:
                    continue

            if not clicked:
                return ActionResult(success=False, action_type="dm", error="DM button not found")

            # Type message
            input_selectors = [
                '[contenteditable="true"]',
                'textarea[placeholder*="message"]',
                'div[role="textbox"]',
                '[data-testid="dmComposerTextInput"]',
                'textarea',
            ]
            for sel in input_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        for char in message:
                            await self._page.keyboard.type(char, delay=random.randint(30, 80))
                        await self._human_delay(0.5, 1)
                        await self._page.keyboard.press("Enter")
                        logger.info(f"DM'd @{handle}")
                        return ActionResult(success=True, action_type="dm")
                except:
                    continue

            return ActionResult(success=False, action_type="dm", error="Message input not found")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            await self._page.goto(group_id, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)
            await self._human_scroll()

            task = f"Extract the first {limit} group members. Return their usernames and display names."
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "display_name": {"type": "string"},
                            },
                        },
                    }
                },
            })

            for item in data.get("users", [])[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except Exception as e:
            logger.error(f"Get group members failed: {e}")
        return results

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        results = []
        try:
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)

            # Try to expand comments
            try:
                more_btn = await self._page.query_selector('button:has-text("View all comments")')
                if more_btn:
                    await more_btn.click()
                    await self._human_delay(1, 2)
            except:
                pass

            await self._human_scroll()

            task = (
                f"Extract the first {limit} users who commented on this post. "
                f"Return their usernames and display names."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "display_name": {"type": "string"},
                            },
                        },
                    }
                },
            })

            for item in data.get("users", [])[:limit]:
                results.append(UserProfile(
                    platform_id=item.get("username", ""),
                    username=item.get("username", ""),
                    display_name=item.get("display_name"),
                ))
        except Exception as e:
            logger.error(f"Get post commenters failed: {e}")
        return results

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)
            await self._human_scroll()

            task = (
                f"Extract the first {limit} comments on this post. "
                f"For each comment, return the author username and comment text."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "comments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "author": {"type": "string"},
                                "text": {"type": "string"},
                            },
                        },
                    }
                },
            })
            return data.get("comments", [])[:limit]
        except Exception as e:
            logger.error(f"Get post comments failed: {e}")
            return []

    async def reply_to_comment(self, comment_id: str, message: str, post_url: Optional[str] = None) -> ActionResult:
        try:
            if post_url:
                await self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                await self._human_delay(1, 2)

            task = (
                f"Find the comment by '{comment_id}' and reply with '{message}'. "
                f"Click the reply button, type the message, and submit."
            )
            await self._extract_with_ai(task)
            return ActionResult(success=True, action_type="reply_comment")
        except Exception as e:
            return ActionResult(success=False, action_type="reply_comment", error=str(e))

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        handle = user_id.lstrip("@")
        url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
        url = url_tmpl.format(handle=handle)
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)
            await self._check_page_for_blockers()

            task = (
                f"Extract from this user profile: "
                f"1. Bio/description text "
                f"2. Display name "
                f"3. Follower count "
                f"4. Whether the account is private "
                f"5. Their 3 most recent post captions"
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "bio": {"type": "string"},
                    "display_name": {"type": "string"},
                    "follower_count": {"type": "string"},
                    "is_private": {"type": "boolean"},
                    "recent_posts": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            })

            return {
                "username": handle,
                "bio": data.get("bio", ""),
                "display_name": data.get("display_name", ""),
                "follower_count": data.get("follower_count", ""),
                "is_private": data.get("is_private", False),
                "recent_posts": data.get("recent_posts", []),
            }
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"username": handle, "bio": "", "display_name": "", "follower_count": "", "is_private": False, "recent_posts": []}

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            handle = user_id.lstrip("@")
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 3)

            task = f"Extract the {limit} most recent posts from this profile. Return their URLs and captions."
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "posts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "caption": {"type": "string"},
                            },
                        },
                    }
                },
            })
            return data.get("posts", [])[:limit]
        except Exception as e:
            logger.error(f"Get recent posts failed: {e}")
            return []

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        try:
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)
            await self._check_page_for_blockers()

            # Find comment input
            input_selectors = [
                '[contenteditable="true"][aria-label*="comment"]',
                'textarea[placeholder*="comment"]',
                'div[role="textbox"]',
                '[contenteditable="true"]',
            ]
            for sel in input_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        for char in message:
                            await self._page.keyboard.type(char, delay=random.randint(30, 80))
                        await self._human_delay(0.5, 1)
                        await self._page.keyboard.press("Enter")
                        logger.info(f"Commented on {post_url}")
                        return ActionResult(success=True, action_type="comment")
                except:
                    continue

            return ActionResult(success=False, action_type="comment", error="Comment input not found")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        try:
            posts = await self.get_user_recent_posts(user_id, limit=1)
            if not posts:
                return ActionResult(success=False, action_type="comment", error="No posts found")
            post_url = posts[0].get("url", "")
            if not post_url:
                return ActionResult(success=False, action_type="comment", error="Post URL empty")
            return await self.comment_on_post(post_url, message)
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def is_following_us(self, target_username: str) -> bool:
        handle = target_username.lstrip("@")
        try:
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)

            text = await self._page.inner_text("body")
            indicators = ["follows you", "follows back", "follows you back"]
            return any(ind in text.lower() for ind in indicators)
        except Exception as e:
            logger.warning(f"is_following_us check for @{handle} failed: {e}")
            return False

    async def capture_screenshot(self) -> Optional[str]:
        try:
            import base64
            ss = await self._page.screenshot(full_page=False)
            return base64.b64encode(ss).decode("utf-8")
        except:
            return None

    # ── Additional methods (used by executor) ──────────────────

    async def view_stories(self, user_id: str) -> bool:
        """View a user's stories if available."""
        handle = user_id.lstrip("@")
        try:
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)

            story_selectors = [
                '[data-testid="story-ring"]',
                'canvas[height="66"]',
                'div[role="button"]:has-text("story")',
                'a[href*="/stories/"]',
            ]
            for sel in story_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await self._human_delay(3, 6)
                        # Close story if close button exists
                        close = await self._page.query_selector('[aria-label="Close"]')
                        if close:
                            await close.click()
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.warning(f"view_stories for @{handle} failed: {e}")
            return False

    async def like_post(self, post_url: str) -> ActionResult:
        """Like a post by URL."""
        try:
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)

            like_selectors = [
                '[data-testid="like"]',
                'button:has-text("Like")',
                '[aria-label*="Like"]',
                'span:has-text("Like")',
                'svg[aria-label="Like"]',
            ]
            for sel in like_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await self._human_delay(0.5, 1)
                        return ActionResult(success=True, action_type="like")
                except:
                    continue

            return ActionResult(success=False, action_type="like", error="Like button not found")
        except Exception as e:
            return ActionResult(success=False, action_type="like", error=str(e))

    async def check_user_followers(self, target_username: str, source_usernames: List[str]) -> Dict[str, Any]:
        """Check if any source accounts appear in target's followers list."""
        handle = target_username.lstrip("@")
        try:
            url_tmpl = PROFILE_URLS.get(self.platform, f"https://www.{self.platform}.com/{{handle}}")
            url = url_tmpl.format(handle=handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 3)

            # Try to open followers list
            followers_selectors = [
                'a:has-text("followers")',
                'a[href*="followers"]',
            ]
            for sel in followers_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el:
                        await el.click()
                        await self._human_delay(2, 3)
                        break
                except:
                    continue

            # Scroll and check for source usernames
            found = []
            for _ in range(10):
                text = await self._page.inner_text("body")
                for src in source_usernames:
                    if src.lower() in text.lower() and src not in [m["username"] for m in found]:
                        found.append({"username": src, "matched": True})
                if found:
                    break
                await self._page.mouse.wheel(0, 500)
                await self._human_delay(0.5, 1)

            return {"found": len(found) > 0, "matched_names": found}
        except Exception as e:
            logger.error(f"check_user_followers for @{handle} failed: {e}")
            return {"found": False, "matched_names": []}

    async def check_inbox(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Check DM inbox for unread messages."""
        try:
            dm_inbox_urls = {
                "instagram": "https://www.instagram.com/direct/inbox/",
                "twitter": "https://x.com/messages",
                "facebook": "https://www.facebook.com/messages/",
                "linkedin": "https://www.linkedin.com/messaging/",
                "tiktok": "https://www.tiktok.com/messages",
            }
            url = dm_inbox_urls.get(self.platform, f"https://www.{self.platform}.com/messages")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)

            task = (
                f"Find conversations with UNREAD messages. "
                f"For each, extract the username and latest message content. "
                f"Return up to {limit} unread conversations."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "unread_conversations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "latest_message": {"type": "string"},
                            },
                        },
                    }
                },
            })
            return data.get("unread_conversations", [])[:limit]
        except Exception as e:
            logger.error(f"Check inbox failed: {e}")
            return []

    async def read_conversation(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Read the last N messages in a DM conversation."""
        handle = user_id.lstrip("@")
        try:
            dm_url = DM_URLS.get(self.platform, "")
            if dm_url:
                url = dm_url.format(uid=handle)
            else:
                url = f"https://www.{self.platform}.com/messages"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 3)

            task = (
                f"Read the last {limit} messages in this conversation. "
                f"For each message, return who sent it ('me' or '{handle}') and the content."
            )
            data = await self._extract_with_ai(task, schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sender": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    }
                },
            })
            return data.get("messages", [])[:limit]
        except Exception as e:
            logger.error(f"Read conversation with @{handle} failed: {e}")
            return []
