"""Shared base for Camoufox-backed platform adapters (TikTok, Facebook).

Contains browser lifecycle, human-like helpers, blocker detection, LLM
decision calls, and the inbox overlay dismissal logic. Subclasses
(`TikTokCamoufoxAdapter`, `FacebookCamoufoxAdapter`) provide only the
platform-specific URL builders, selectors, and `authenticate()` quirks.
"""

import asyncio
import json
import logging
import os
import random
from typing import Optional

from playwright.async_api import BrowserContext, Page

from app.exceptions import BlockerDetected
from app.platforms.base import PlatformAdapter

logger = logging.getLogger("BaseCamoufoxAdapter")

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


class BaseCamoufoxAdapter(PlatformAdapter):
    """Anti-detection adapter using Camoufox (patched Firefox) + Playwright.

    Subclasses MUST set `platform_name` and `platform_label` (e.g. "tiktok").
    """

    platform_name: str = "base"
    platform_label: str = "base"

    def __init__(self, platform: str = "", **kwargs):
        self.platform = (platform or self.platform_label).lower()
        self.platform_name = self.platform
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._session_data: Optional[str] = None
        self._camoufox = None
        self._current_username: Optional[str] = None

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

        logger.info(f"Launching Camoufox browser for {self.platform}...")
        self._camoufox = AsyncCamoufox(**launch_kwargs)
        try:
            self._context = await self._camoufox.__aenter__()
        except Exception as e:
            logger.warning(f"Camoufox launch failed, retrying without proxy: {e}")
            self._camoufox = AsyncCamoufox(headless=True, os=["windows", "macos"])
            self._context = await self._camoufox.__aenter__()

        # Camoufox may return Browser or BrowserContext — get the context either way
        if hasattr(self._context, "new_context"):
            self._context = await self._context.new_context()

        if session_data:
            await self._load_cookies(session_data)

        self._page = await self._context.new_page()
        logger.info("Camoufox browser ready")

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
        if not url.startswith(("http://", "https://", "socks5://")):
            url = f"http://{url}"
        username = os.getenv("SKYVERN_PROXY_USERNAME", "").strip()
        password = os.getenv("SKYVERN_PROXY_PASSWORD", "").strip()
        config = {"url": url}
        if username:
            config["username"] = username
            config["password"] = password
        return config

    # ── Human-like helpers ──────────────────────────────────────────────

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
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)
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

    # ── Overlay dismissal (shared with all Camoufox adapters) ────────────

    async def _dismiss_overlay(self):
        """Close any inbox/notification/DM overlays that the platform opens by default."""
        for attempt in range(5):
            try:
                removed = await self._page.evaluate('''() => {
                    const app = document.querySelector("#app");
                    if (app) {
                        app.removeAttribute("inert");
                        app.removeAttribute("aria-hidden");
                        app.removeAttribute("data-floating-ui-inert");
                    }

                    document.querySelectorAll('[data-floating-ui-portal]').forEach(el => {
                        if (el.querySelector('.TUXModal-overlay, [class*="Modal-overlay"], [class*="modal-overlay"]')) {
                            el.style.display = "none";
                            el.remove();
                        }
                    });

                    document.querySelectorAll('.TUXModal-overlay, [class*="Modal-overlay"], [class*="modal-overlay"]').forEach(el => {
                        el.style.display = "none";
                        el.remove();
                    });

                    return true;
                }''')

                if removed:
                    await self._human_delay(0.5, 1)

                is_inert = await self._page.evaluate(
                    'document.querySelector("#app")?.getAttribute("inert") === "true"'
                )
                if not is_inert:
                    break

                logger.info(f"Overlay still present (inert=true), attempt {attempt+1}")
                await self._page.keyboard.press("Escape")
                await self._human_delay(1, 2)
            except: break

    # ── Shared utilities ────────────────────────────────────────────────

    def _parse_count_text(self, text: str) -> int:
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
        self._current_username = None
