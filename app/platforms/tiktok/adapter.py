"""TikTok adapter using Camoufox (patched Firefox) for anti-detection.

All browser lifecycle, human-like helpers, blocker detection, and LLM
decision logic live in `BaseCamoufoxAdapter`. This file only contains
TikTok-specific URL builders, selectors, and `authenticate()` quirks.
"""

import json
import logging
import os
import random
import re
from typing import Optional, List, Dict, Any

from playwright.async_api import Page

from app.exceptions import BlockerDetected
from app.platforms.base import ActionResult, UserProfile
from app.platforms.shared.base_camoufox import BaseCamoufoxAdapter

logger = logging.getLogger("TikTokCamoufoxAdapter")


class TikTokCamoufoxAdapter(BaseCamoufoxAdapter):
    """Anti-detection adapter for TikTok using Camoufox + Playwright."""

    platform_name: str = "tiktok"
    platform_label: str = "tiktok"

    # ── URL helpers ────────────────────────────────────────────────────

    @staticmethod
    def _profile_url(handle: str) -> str:
        return f"https://www.tiktok.com/@{handle.lstrip('@')}"

    @staticmethod
    def _post_url(handle: str, post_id: str) -> str:
        return f"https://www.tiktok.com/@{handle.lstrip('@')}/video/{post_id}"

    # ── Authentication ────────────────────────────────────────────────

    async def authenticate(
        self,
        session_data: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        try:
            await self._ensure_browser(session_data)
            home_url = "https://www.tiktok.com/"
            await self._navigate(home_url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, home_url)
            logged_in = not any(w in text.lower() for w in ["log in", "sign in", "sign up"])
            logger.info(f"Auth check: logged_in={logged_in}")

            if logged_in:
                try:
                    page_source = await self._page.content()
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

    # ── User discovery ─────────────────────────────────────────────────

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = f"https://www.tiktok.com/search?q={query}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

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
            url = f"https://www.tiktok.com/@{handle}/followers"
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            prev_count = 0
            for i in range(15):
                await self._page.mouse.wheel(0, 1500)
                await self._human_delay(1.5, 2.5)
                links = await self._page.query_selector_all('a[href*="/@"]')
                curr_count = len(links)
                if curr_count == prev_count and i > 3:
                    break
                prev_count = curr_count

            text = await self._extract_page_text()

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

            if usernames:
                for u in usernames[:limit]:
                    results.append(UserProfile(platform_id=u, username=u))
                logger.info(f"Extracted {len(results)} followers from HTML")
            else:
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

    # ── Follow / unfollow ─────────────────────────────────────────────

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = self._profile_url(handle)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

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
            url = self._profile_url(handle)
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

    # ── Direct messages ───────────────────────────────────────────────

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = self._profile_url(handle)
            logger.info(f"send_dm: Navigating to {url}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(5, 7)

            page_text = await self._extract_page_text()
            self._check_for_blockers(page_text, url)

            page_source = await self._page.content()
            uid_match = re.search(r'(?<="userInfo":\{"user":\{"id":")\d{1,30}', page_source)
            if not uid_match:
                uid_match = re.search(r'"id"\s*:\s*"(\d{1,30})"', page_source)
            if not uid_match:
                logger.warning(f"send_dm: Could not extract user_id for @{handle}")
                return ActionResult(success=False, action_type="dm", error="Could not extract user_id")
            uid = uid_match.group(1) if uid_match.lastindex else uid_match.group(0)
            logger.info(f"send_dm: Got user_id={uid} for @{handle}")

            dm_url = f"https://www.tiktok.com/messages?lang=en&u={uid}"
            logger.info(f"send_dm: Navigating to DM page: {dm_url}")
            await self._page.goto(dm_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            dm_loaded = False
            for attempt in range(5):
                try:
                    if "/login" in self._page.url:
                        logger.warning("send_dm: Redirected to login page — not logged in")
                        return ActionResult(success=False, action_type="dm", error="Not logged in")

                    chat_header = self._page.locator('p[data-e2e="chat-uniqueid"]')
                    if await chat_header.count() > 0:
                        dm_loaded = True
                        logger.info("send_dm: DM page loaded (chat-uniqueid found)")
                        break

                    input_box = self._page.locator('div[aria-label="Send a message..."][role="textbox"]')
                    if await input_box.count() > 0:
                        dm_loaded = True
                        logger.info("send_dm: DM page loaded (input box found)")
                        break

                    await self._human_delay(2, 3)
                except:
                    await self._human_delay(2, 3)

            if not dm_loaded:
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

                try:
                    warn_el = self._page.locator('div[data-e2e="dm-warning"]')
                    if await warn_el.count() > 0:
                        warn_text = await warn_el.inner_text()
                        logger.warning(f"send_dm: DM warning — {warn_text}")
                        return ActionResult(success=False, action_type="dm", error=f"DM warning: {warn_text}")
                except: pass

                try:
                    await self._page.screenshot()
                    logger.warning(f"send_dm: DM page not loaded. URL: {self._page.url}")
                except: pass

                return ActionResult(success=False, action_type="dm", error="DM page not loaded")

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
                return ActionResult(success=False, action_type="dm", error="DM input not found")

            logger.info(f"send_dm: Typing message ({len(message)} chars)")
            await dm_input.click()
            await self._page.keyboard.press("Control+KeyA")
            await self._page.keyboard.press("Backspace")
            await self._human_delay(0.3, 0.5)

            await self._page.evaluate(f"navigator.clipboard.writeText({repr(message)})")
            await self._page.keyboard.press("Control+KeyV")
            await self._human_delay(0.5, 1)

            send_btn = self._page.locator('[class*="StyledSendButton"]').first
            try:
                if await send_btn.count() > 0:
                    await send_btn.wait_for(state="visible", timeout=5000)
                    await send_btn.click(timeout=5000)
                else:
                    await self._page.keyboard.press("Enter")
            except:
                await self._page.keyboard.press("Enter")

            await self._human_delay(1, 2)
            logger.info(f"send_dm: DM sent to @{handle}")
            return ActionResult(success=True, action_type="dm")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"send_dm FAILED for @{user_id}: {e}")
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def reply_to_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            await self._navigate(f"https://www.tiktok.com/direct/t/{handle}")
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text)

            msg_input = self._page.locator("textarea, div[contenteditable='true'], div[data-e2e='message-input']").first
            await msg_input.click(timeout=15000)
            await self._human_delay(0.5, 1)

            for char in message:
                await msg_input.type(char, delay=random.randint(50, 150))
            await self._human_delay(0.5, 1)

            send_btn = self._page.get_by_role("button", name="Send").first
            await send_btn.click(timeout=15000)
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="reply_dm")
        except BlockerDetected:
            raise
        except Exception as e:
            return ActionResult(success=False, action_type="reply_dm", error=str(e))

    # ── Inbox / conversations ──────────────────────────────────────────

    async def check_inbox(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate("https://www.tiktok.com/direct/inbox")
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
            await self._navigate(f"https://www.tiktok.com/direct/t/{handle}")
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

    # ── Groups ────────────────────────────────────────────────────────

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

    # ── Posts & comments ──────────────────────────────────────────────

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)

            # Inject MutationObserver to auto-remove inert whenever TikTok re-applies it
            await self._page.evaluate('''() => {
                if (window.__inertObserver) return;
                window.__inertObserver = true;
                const observer = new MutationObserver((mutations) => {
                    for (const m of mutations) {
                        if (m.type === "attributes" && m.attributeName === "inert") {
                            const el = m.target;
                            if (el.id === "app" && el.getAttribute("inert") === "true") {
                                el.removeAttribute("inert");
                                el.removeAttribute("aria-hidden");
                                el.removeAttribute("data-floating-ui-inert");
                            }
                        }
                    }
                });
                const app = document.querySelector("#app");
                if (app) {
                    observer.observe(app, { attributes: true, attributeFilter: ["inert"] });
                }
                document.querySelectorAll('[data-floating-ui-portal]').forEach(el => el.remove());
                if (app && app.getAttribute("inert") === "true") {
                    app.removeAttribute("inert");
                    app.removeAttribute("aria-hidden");
                    app.removeAttribute("data-floating-ui-inert");
                }
            }''')

            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(5, 7)

            await self._page.evaluate('''() => {
                const app = document.querySelector("#app");
                if (app && app.getAttribute("inert") === "true") {
                    app.removeAttribute("inert");
                    app.removeAttribute("aria-hidden");
                    app.removeAttribute("data-floating-ui-inert");
                }
                document.querySelectorAll('[data-floating-ui-portal]').forEach(el => el.remove());
            }''')
            await self._human_delay(1, 2)

            video_owner = ""
            try:
                video_owner = post_url.split("/@")[-1].split("/")[0].split("?")[0].lower()
            except: pass

            for _ in range(10):
                await self._page.mouse.wheel(0, 600)
                await self._human_delay(1.5, 2.5)
            await self._human_delay(2, 3)
            await self._page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(1, 2)

            comment_links = []
            container_found = ""

            container_selectors = [
                '[data-e2e="browse-comment-list"]',
                '[data-e2e="comment-list"]',
            ]
            for sel in container_selectors:
                try:
                    container = self._page.locator(sel).first
                    if await container.count() > 0:
                        links = await container.locator('a[href*="/@"]').all()
                        if links:
                            comment_links = links
                            container_found = sel
                            logger.info(f"get_post_commenters: found '{sel}' with {len(links)} user links")
                            break
                except: pass

            if not comment_links:
                avatar_selectors = [
                    '[data-e2e="comment-avatar-1"]',
                    '[data-e2e="comment-avatar-2"]',
                    '[data-e2e="comment-avatar-3"]',
                ]
                for sel in avatar_selectors:
                    try:
                        links = await self._page.query_selector_all(sel)
                        if links:
                            comment_links = links
                            container_found = sel
                            logger.info(f"get_post_commenters: found avatar selector '{sel}' with {len(links)} links")
                            break
                    except: pass

            if not comment_links:
                for level_sel in ['[data-e2e="comment-level-1"]', '[data-e2e="comment-level-2"]']:
                    try:
                        spans = await self._page.query_selector_all(level_sel)
                        if spans:
                            for span in spans[:limit]:
                                try:
                                    parent = await span.evaluate_handle(
                                        "el => el.closest('[data-e2e=\"comment-item\"]') || el.parentElement.parentElement"
                                    )
                                    if parent:
                                        links_in_parent = await parent.query_selector_all('a[href*="/@"]')
                                        if links_in_parent:
                                            comment_links.extend(links_in_parent)
                                except: pass
                            if comment_links:
                                container_found = level_sel
                                logger.info(f"get_post_commenters: found {len(comment_links)} links via '{level_sel}'")
                                break
                    except: pass

            if not comment_links:
                clicked = False
                for btn_sel in [
                    '[data-e2e="comment-icon"]',
                    '[data-e2e="browse-comment-icon"]',
                    'span[data-e2e="comment-icon"]',
                    '[data-e2e="like-comment"]',
                ]:
                    try:
                        btn = self._page.locator(btn_sel).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=5000)
                            await self._human_delay(3, 4)
                            logger.info(f"get_post_commenters: clicked '{btn_sel}', waiting for comments")
                            clicked = True
                            break
                    except: pass

                if not clicked:
                    try:
                        comment_btns = await self._page.query_selector_all(
                            '[aria-label*="comment" i], [aria-label*="Comment" i], '
                            '[data-e2e*="comment"], span[role="img"][aria-label*="comment" i]'
                        )
                        for btn in comment_btns:
                            try:
                                if await btn.is_visible():
                                    await btn.click(timeout=5000)
                                    await self._human_delay(3, 4)
                                    logger.info(f"get_post_commenters: clicked comment button via aria-label fallback")
                                    clicked = True
                                    break
                            except: pass
                    except: pass

                if not clicked:
                    try:
                        bars = await self._page.query_selector_all('section')
                        for bar in bars:
                            cls = await bar.get_attribute("class") or ""
                            if "Action" in cls or "action" in cls:
                                children = await bar.query_selector_all(':scope > *')
                                if len(children) >= 2:
                                    await children[1].click(timeout=5000)
                                    await self._human_delay(3, 4)
                                    logger.info(f"get_post_commenters: clicked 2nd child of action bar section")
                                    clicked = True
                                    break
                    except: pass

                for sel in container_selectors + avatar_selectors:
                    try:
                        if sel.startswith('[data-e2e="comment-avatar'):
                            links = await self._page.query_selector_all(sel)
                        else:
                            container = self._page.locator(sel).first
                            links = await container.locator('a[href*="/@"]').all() if await container.count() > 0 else []
                        if links:
                            comment_links = links
                            container_found = sel
                            logger.info(f"get_post_commenters: after click, found '{sel}' with {len(links)} links")
                            break
                    except: pass

                if not comment_links:
                    try:
                        all_e2e_after = await self._page.query_selector_all('[data-e2e]')
                        e2e_after = []
                        for el in all_e2e_after[:50]:
                            try:
                                val = await el.get_attribute("data-e2e")
                                if val:
                                    e2e_after.append(val)
                            except: pass
                        logger.warning(f"get_post_commenters: after click, data-e2e dump: {e2e_after}")
                        ss_path2 = os.path.join(os.path.dirname(__file__), "..", "..", "..", "debug_post_after_click.png")
                        await self._page.screenshot(path=ss_path2, full_page=False)
                        logger.warning(f"get_post_commenters: Screenshot after click saved to {ss_path2}")
                    except: pass

            if not comment_links:
                try:
                    all_e2e = await self._page.query_selector_all('[data-e2e]')
                    e2e_vals = []
                    for el in all_e2e[:50]:
                        try:
                            val = await el.get_attribute("data-e2e")
                            if val:
                                e2e_vals.append(val)
                        except: pass
                    logger.warning(f"get_post_commenters: NO COMMENTS FOUND. Page data-e2e dump: {e2e_vals}")

                    sections = await self._page.query_selector_all('section')
                    logger.warning(f"get_post_commenters: Found {len(sections)} <section> elements")
                    for i, sec in enumerate(sections[:10]):
                        try:
                            aria = await sec.get_attribute("aria-label") or ""
                            cls = (await sec.get_attribute("class") or "")[:60]
                            child_count = await sec.evaluate("el => el.children.length")
                            inner = await sec.inner_html()
                            logger.warning(f"  section[{i}]: aria='{aria}' class='{cls}' children={child_count}")
                            logger.warning(f"  section[{i}] innerHTML (first 2000): {inner[:2000]}")
                        except: pass

                    buttons = await self._page.query_selector_all('button, [role="button"], [data-e2e*="comment"], [aria-label*="comment" i], [aria-label*="Comment" i]')
                    logger.warning(f"get_post_commenters: Found {len(buttons)} button/comment elements")
                    for i, btn in enumerate(buttons[:20]):
                        try:
                            tag = await btn.evaluate("el => el.tagName")
                            aria = await btn.get_attribute("aria-label") or ""
                            e2e = await btn.get_attribute("data-e2e") or ""
                            cls = (await btn.get_attribute("class") or "")[:60]
                            text = (await btn.inner_text())[:50] if await btn.is_visible() else "[hidden]"
                            logger.warning(f"  btn[{i}]: <{tag}> aria='{aria}' e2e='{e2e}' class='{cls}' text='{text}'")
                        except: pass

                    ss_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "debug_post_page.png")
                    await self._page.screenshot(path=ss_path, full_page=False)
                    logger.warning(f"get_post_commenters: Screenshot saved to {ss_path}")

                    main_html = await self._page.evaluate("""
                        () => {
                            const main = document.querySelector('[data-e2e="browse-main"]')
                                || document.querySelector('main')
                                || document.querySelector('#app')
                                || document.body;
                            return main.outerHTML.substring(0, 5000);
                        }
                    """)
                    logger.warning(f"get_post_commenters: Main content HTML (first 5000): {main_html}")
                except Exception as e:
                    logger.error(f"get_post_commenters: debug dump failed: {e}")

                return results

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
                logger.info(f"Extracted {len(results)} commenters (container: {container_found})")
            else:
                logger.info("get_post_commenters: found links but all filtered out (owner/duplicate)")
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

    # ── Profiles & posts ──────────────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        handle = user_id.lstrip("@")
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            is_private = False

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

            if not is_private:
                try:
                    grid = await self._page.query_selector('[data-e2e="user-post-item"], [data-e2e="user-post-grid"]')
                    if not grid:
                        if "follow" in text_lower and ("see" in text_lower or "photos" in text_lower or "videos" in text_lower):
                            is_private = True
                            logger.info(f"Private account detected (no grid + follow text): @{handle}")
                except: pass

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
            url = self._profile_url(handle)
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            for _ in range(5):
                await self._page.mouse.wheel(0, 1200)
                await self._human_delay(1.5, 2.5)

            posts = []
            try:
                links = await self._page.query_selector_all('a[href*="/video/"], a[href*="/photo/"]')
                seen_ids = set()
                for link in links[:limit * 5]:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    if f"/@{handle}/" not in href and f"/@{handle}?" not in href:
                        continue
                    vid_match = re.search(r'/(video|photo)/(\d+)', href)
                    if not vid_match:
                        continue
                    vid_id = vid_match.group(2)
                    if vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)
                    if not href.startswith("http"):
                        href = f"https://www.tiktok.com{href}"
                    posts.append({"url": href, "caption": ""})
                    if len(posts) >= limit:
                        break
                if posts:
                    logger.info(f"Extracted {len(posts)} posts from HTML for @{handle}")
                    return posts
            except Exception as e:
                logger.warning(f"HTML post extraction failed: {e}")

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
            url = self._profile_url(handle)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

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

    # ── Screenshot ────────────────────────────────────────────────────

    async def capture_screenshot(self) -> Optional[str]:
        try:
            if self._page:
                screenshot = await self._page.screenshot(type="png")
                import base64
                return base64.b64encode(screenshot).decode()
        except Exception:
            pass
        return None

    # ── Likes / share / stories / live ─────────────────────────────────

    async def like_post(self, post_url: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            await self._page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            await self._page.evaluate('''() => {
                const app = document.querySelector("#app");
                if (app && app.getAttribute("inert") === "true") {
                    app.removeAttribute("inert");
                    app.removeAttribute("aria-hidden");
                    app.removeAttribute("data-floating-ui-inert");
                }
                document.querySelectorAll('[data-floating-ui-portal]').forEach(el => el.remove());
            }''')
            await self._human_delay(1, 2)

            like_btn = None
            selectors = [
                '//button[.//span[@data-e2e="browse-like-icon" or @data-e2e="like-icon"]]',
                'button[data-e2e="like-icon"]',
                'button[data-e2e="like-button"]',
                '[data-e2e="like-icon"]',
                '[data-e2e="like-button"]',
                'button[aria-label*="Like"]',
                'button[aria-label*="like"]',
                'div[class*="StyledIconWrapper"]:first-of-type',
                'div[class*="StyledIconWrapper"]:first-of-type svg',
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

                    e2e_els = await self._page.query_selector_all('[data-e2e]')
                    logger.warning(f"like_post: Found {len(e2e_els)} elements with data-e2e:")
                    for i, el in enumerate(e2e_els[:30]):
                        try:
                            e2e = await el.get_attribute("data-e2e") or ""
                            tag = await el.evaluate("el => el.tagName")
                            logger.warning(f"  data-e2e[{i}]: <{tag}> data-e2e='{e2e}'")
                        except: pass

                    aria_divs = await self._page.query_selector_all('div[aria-label]')
                    logger.warning(f"like_post: Found {len(aria_divs)} divs with aria-label:")
                    for i, el in enumerate(aria_divs[:20]):
                        try:
                            aria = await el.get_attribute("aria-label") or ""
                            logger.warning(f"  div-aria[{i}]: aria-label='{aria}'")
                        except: pass

                    svgs = await self._page.query_selector_all('svg')
                    logger.warning(f"like_post: Found {len(svgs)} SVGs on page")
                    for i, svg in enumerate(svgs[:15]):
                        try:
                            parent_tag = await svg.evaluate("el => el.parentElement ? el.parentElement.tagName + '.' + (el.parentElement.className || '').substring(0,50) : 'none'")
                            aria = await svg.get_attribute("aria-label") or ""
                            logger.warning(f"  svg[{i}]: parent='{parent_tag}' aria='{aria}'")
                        except: pass

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
        try:
            await self._ensure_browser(self._session_data)
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

            share_btn = self._page.locator(
                "button[data-e2e='share-icon'], "
                "button[data-e2e='share-button'], "
                "span[data-e2e='share-icon'], "
                "button[aria-label*='Share'], "
                "button[aria-label*='share']"
            ).first
            await share_btn.click(timeout=15000)
            await self._human_delay(1, 2)

            try:
                repost_btn = self._page.get_by_role("button", name="Repost").first
                await repost_btn.click(timeout=8000)
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
            handle = user_id.lstrip("@")
            url = self._profile_url(handle)
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            story_btn = self._page.locator(
                "div[data-e2e='story-avatar'], "
                "div[data-e2e='user-avatar'][data-e2e='has-story'], "
                "a[href*='/story']"
            ).first
            await story_btn.click(timeout=15000)
            await self._human_delay(3, 5)

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
        try:
            await self._ensure_browser(self._session_data)
            handle = user_id.lstrip("@")
            url = self._profile_url(handle)
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

    # ── Follower-based safety checks ──────────────────────────────────

    async def check_user_followers(self, username: str, search_names: List[str]) -> Dict[str, Any]:
        try:
            await self._ensure_browser(self._session_data)
            handle = username.lstrip("@")
            url = self._profile_url(handle)
            logger.info(f"check_user_followers: Checking followers of @{handle}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

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

            follower_count = 0
            try:
                count_el = self._page.locator('[data-e2e="followers-count"]').first
                if await count_el.count() > 0:
                    count_text = await count_el.inner_text()
                    follower_count = self._parse_count_text(count_text)
            except: pass

            matched = []
            search_lower = [n.lower().replace(".", " ").replace("_", " ").replace("-", " ") for n in search_names]

            seen = set()
            for scroll_i in range(20):
                try:
                    items = await self._page.query_selector_all('[data-e2e="search-user-container"], div[class*="follow-item"], div[class*="FollowerItem"]')
                    if not items:
                        items = await self._page.query_selector_all('a[href*="/@"]')
                except:
                    items = []

                new_found = False
                for item in items:
                    try:
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

                        display_name = ""
                        try:
                            name_el = await item.query_selector('p[class*="nickname"], span[class*="nickname"], h3, h4')
                            if name_el:
                                display_name = (await name_el.inner_text()).lower()
                        except: pass

                        combined = f"{item_username} {display_name}".replace(".", " ").replace("_", " ").replace("-", " ")
                        for search_name in search_lower:
                            search_words = search_name.split()
                            if len(search_words) >= 2:
                                matches = sum(1 for w in search_words if w in combined)
                                if matches >= len(search_words) - 1:
                                    matched.append({"username": item_username, "display_name": display_name, "matched_search": search_name})
                                    logger.info(f"check_user_followers: FOUND match '@{item_username}' ({display_name}) for '{search_name}'")
                            else:
                                if search_words[0] in combined and len(search_words[0]) >= 3:
                                    matched.append({"username": item_username, "display_name": display_name, "matched_search": search_name})
                                    logger.info(f"check_user_followers: FOUND match '@{item_username}' ({display_name}) for '{search_name}'")
                    except: pass

                if matched:
                    break

                if not new_found and scroll_i > 2:
                    break

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
        followers = set()
        try:
            await self._ensure_browser(self._session_data)
            handle = username.lstrip("@")
            url = self._profile_url(handle)
            logger.info(f"get_target_followers: Scraping followers of @{handle}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

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

            prev_count = 0
            for i in range(max_scroll):
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

    # ── Clone / fake account search ──────────────────────────────────

    async def search_for_clones(self, target_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            await self._ensure_browser(self._session_data)
            clean_name = target_name.replace(".", " ").replace("_", " ").replace("-", " ").strip()
            search_url = f"https://www.tiktok.com/search/user?q={clean_name}&lang=en"
            logger.info(f"search_for_clones: Searching for '{clean_name}'")
            await self._page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await self._human_delay(3, 5)

            for _ in range(3):
                await self._page.mouse.wheel(0, 1000)
                await self._human_delay(1, 2)

            results = []
            try:
                cards = await self._page.query_selector_all('[data-e2e="search-user-container"], div[class*="user-card"], div[class*="UserCard"]')
                if not cards:
                    cards = await self._page.query_selector_all('a[href*="/@"]')

                seen_usernames = set()
                for card in cards[:limit * 2]:
                    try:
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
