"""Facebook adapter using Camoufox (patched Firefox) for anti-detection.

All browser lifecycle, human-like helpers, blocker detection, and LLM
decision logic live in `BaseCamoufoxAdapter`. This file only contains
Facebook-specific URL builders, selectors, and the optional
email/password login flow used when cookies are missing.
"""

import json
import logging
import random
import re
from typing import Optional, List, Dict, Any

from app.exceptions import BlockerDetected
from app.platforms.base import ActionResult, UserProfile
from app.platforms.shared.base_camoufox import BaseCamoufoxAdapter

logger = logging.getLogger("FacebookCamoufoxAdapter")


class FacebookCamoufoxAdapter(BaseCamoufoxAdapter):
    """Anti-detection adapter for Facebook using Camoufox + Playwright."""

    platform_name: str = "facebook"
    platform_label: str = "facebook"

    # ── URL helpers ────────────────────────────────────────────────────

    @staticmethod
    def _profile_url(user_id: str) -> str:
        uid = user_id.lstrip("@")
        if uid.isdigit():
            return f"https://www.facebook.com/profile.php?id={uid}"
        return f"https://www.facebook.com/{uid}"

    @staticmethod
    def _dm_url(user_id: str) -> str:
        uid = user_id.lstrip("@")
        return f"https://www.facebook.com/messages/t/{uid}"

    @staticmethod
    def _group_url(group_id: str) -> str:
        gid = group_id.lstrip("/")
        if gid.startswith("https://"):
            return gid
        return f"https://www.facebook.com/groups/{gid}"

    # ── Authentication ────────────────────────────────────────────────

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
        try:
            await self._navigate("https://www.facebook.com/login")
            await self._human_delay(2, 3)

            email_input = self._page.locator(
                'input[name="email"], input#email, input[placeholder*="Email"], input[placeholder*="Phone"]'
            ).first
            await email_input.click(timeout=5000)
            await email_input.fill(username)
            await self._human_delay(0.5, 1)

            pass_input = self._page.locator(
                'input[name="pass"], input#pass, input[type="password"]'
            ).first
            await pass_input.click(timeout=5000)
            await pass_input.fill(password)
            await self._human_delay(0.5, 1)

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

    # ── User discovery ─────────────────────────────────────────────────

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = f"https://www.facebook.com/search/people/?q={query}"
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            for _ in range(5):
                await self._page.mouse.wheel(0, 800)
                await self._human_delay(1.5, 2.5)

            text = await self._extract_page_text()

            usernames = []
            try:
                links = await self._page.locator('a[role="link"]').all()
                seen = set()
                for link in links[:limit * 3]:
                    href = await link.get_attribute("href")
                    if not href or "/groups/" in href or "/events/" in href:
                        continue
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

    # ── Follow / unfollow ─────────────────────────────────────────────

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._profile_url(user_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

            try:
                add_friend_btn = self._page.get_by_role("button", name="Add Friend").first
                await add_friend_btn.click(timeout=5000)
                await self._human_delay(1, 2)
                return ActionResult(success=True, action_type="add_friend")
            except Exception:
                pass

            try:
                follow_btn = self._page.get_by_role("button", name="Follow").first
                await follow_btn.click(timeout=5000)
                await self._human_delay(1, 2)
                return ActionResult(success=True, action_type="follow")
            except Exception:
                pass

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

            for btn_name in ["Following", "Friends", "Friend"]:
                btn = self._page.get_by_role("button", name=btn_name).first
                try:
                    await btn.click(timeout=5000)
                    await self._human_delay(1, 2)
                    try:
                        confirm = self._page.get_by_role("button", name="Unfriend").first
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

    # ── Direct messages ───────────────────────────────────────────────

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._ensure_browser(self._session_data)
            url = self._dm_url(user_id)
            await self._navigate(url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

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

            await msg_input.press("Enter")
            await self._human_delay(1, 2)
            return ActionResult(success=True, action_type="dm")
        except BlockerDetected:
            raise
        except Exception as e:
            logger.error(f"send_dm failed for {user_id}: {e}")
            return ActionResult(success=False, action_type="dm", error=str(e))

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

    # ── Inbox / conversations ──────────────────────────────────────────

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

    # ── Groups ────────────────────────────────────────────────────────

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            await self._ensure_browser(self._session_data)
            url = self._group_url(group_id)
            await self._navigate(url)
            text = await self._extract_page_text()
            self._check_for_blockers(text, url)

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

    # ── Posts & comments ──────────────────────────────────────────────

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        results = []
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

    # ── Profiles & posts ──────────────────────────────────────────────

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
            await self._navigate(post_url)
            await self._human_delay(2, 3)
            text = await self._extract_page_text()
            self._check_for_blockers(text, post_url)

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

            story_btn = self._page.locator(
                'div[aria-label*="Story"], '
                'a[href*="/stories/"]'
            ).first
            await story_btn.click(timeout=5000)
            await self._human_delay(5, 7)

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
