import asyncio
import logging
import json
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, TimeoutError
from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

class InstagramAdapter(PlatformAdapter):
    platform_name = "instagram"

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger("InstagramAdapter")

    async def authenticate(self, session_data: Optional[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login using saved cookies or fallback to credentials.
        """
        try:
            if session_data:
                cookies = json.loads(session_data)
                await self.page.context.add_cookies(cookies)
                await self.page.goto("https://www.instagram.com/")
                # Check if logged in
                try:
                    await self.page.wait_for_selector('svg[aria-label="New post"]', timeout=5000)
                    return True
                except:
                    self.logger.warning("Session cookies expired. Trying credentials...")

            if username and password:
                await self.page.goto("https://www.instagram.com/accounts/login/")
                await self.page.get_by_label("Phone number, username, or email").fill(username)
                await self.page.get_by_label("Password").fill(password)
                await self.page.get_by_role("button", name="Log in", exact=True).click()
                
                # Wait for navigation or verification
                try:
                    await self.page.wait_for_selector('svg[aria-label="New post"]', timeout=15000)
                    return True
                except:
                    self.logger.error("Login failed with provided credentials.")
                    return False

            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def get_current_cookies(self) -> str:
        cookies = await self.page.context.cookies()
        return json.dumps(cookies)

    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        results = []
        try:
            # Click search
            # Note: Selectors are fragile. Using aria-labels is often better.
            search_icon = self.page.get_by_role("link", name="Search")
            if await search_icon.count() > 0:
                await search_icon.click()
            else:
                # Try mobile layout or different view
                await self.page.goto(f"https://www.instagram.com/explore/search/keyword/?q={query}")

            input_box = self.page.get_by_placeholder("Search")
            await input_box.fill(query)
            await self.page.wait_for_timeout(2000) # Wait for results

            # Scrape results
            # This is a simplification. Real scraping needs robust loop.
            # Assuming a list of results appears
            links = await self.page.query_selector_all('a[href^="/"][role="link"]')

            count = 0
            for link in links:
                if count >= limit: break
                href = await link.get_attribute("href")
                username = href.strip("/").split("/")[0] # Rough extraction

                # Filter out non-user links
                if username in ["explore", "reels", "direct"]: continue

                results.append(UserProfile(
                    platform_id=username, # Use username as ID for IG
                    username=username,
                    display_name=username # Placeholder
                ))
                count += 1

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        # This is complex in IG. Needs clicking "Followers" and scrolling.
        followers = []
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            # Click followers link
            await self.page.get_by_text("followers").click()
            await self.page.wait_for_selector('div[role="dialog"]', timeout=5000)

            dialog = self.page.locator('div[role="dialog"]')
            # Scroll loop would go here

            # Placeholder scraping
            # In a real impl, we'd scroll the list inside the dialog.
            # For this Phase, I will just grab what's visible.
            items = await dialog.locator('a[href^="/"]').all()
            for item in items:
                href = await item.get_attribute("href")
                u = href.strip("/")
                followers.append(UserProfile(platform_id=u, username=u))
                if len(followers) >= limit: break

        except Exception as e:
            self.logger.error(f"Get followers failed: {e}")

        return followers

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            # Look for Follow button
            # It could be "Follow", "Requested", "Following"
            btn = self.page.get_by_role("button", name="Follow", exact=True)

            if await btn.count() > 0:
                await btn.click()
                # Verify change to "Following" or "Requested"
                # await expect(btn).not_to_be_visible()
                return ActionResult(success=True, action_type="follow")
            else:
                return ActionResult(success=False, action_type="follow", error="Already following or button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            btn = self.page.get_by_role("button", name="Following")
            if await btn.count() > 0:
                await btn.click()
                # Confirm dialog often appears
                unfollow_confirm = self.page.get_by_role("button", name="Unfollow")
                if await unfollow_confirm.count() > 0:
                    await unfollow_confirm.click()
                return ActionResult(success=True, action_type="unfollow")

            return ActionResult(success=False, action_type="unfollow", error="Not following")

        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            # Go to profile, click Message
            await self.page.goto(f"https://www.instagram.com/{user_id}/")

            msg_btn = self.page.get_by_role("button", name="Message")
            if await msg_btn.count() > 0:
                await msg_btn.click()

                # Wait for chat box
                box = self.page.get_by_role("textbox", name="Message")
                await box.fill(message)
                await box.press("Enter")

                return ActionResult(success=True, action_type="dm")

            return ActionResult(success=False, action_type="dm", error="Message button not found")

        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        """On Instagram, we map group combing to mining followers of a target account"""
        self.logger.info(f"Combing Instagram (mining followers of {group_id})")
        return await self.get_followers(group_id, limit=limit)

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        """Scrape users who commented on an Instagram post"""
        self.logger.info(f"Combing Instagram commenters: {post_url}")
        # Placeholder: Navigate to post and scrape commenters
        return []

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments from an Instagram post"""
        self.logger.info(f"Fetching comments from Instagram post: {post_url}")
        # Placeholder implementation
        comments = []
        # TODO: Implement actual comment scraping
        return comments

    async def reply_to_comment(self, comment_id: str, message: str) -> ActionResult:
        """Reply to a specific comment on Instagram"""
        self.logger.info(f"Replying to Instagram comment {comment_id}")
        # Placeholder implementation
        # TODO: Implement actual comment reply
        return ActionResult(success=False, action_type="reply_comment", error="Not implemented")

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent posts from an Instagram user"""
        self.logger.info(f"Fetching recent posts from Instagram user: {user_id}")
        # Placeholder implementation
        posts = []
        # TODO: Implement actual post fetching
        return posts

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        """Comment on a specific Instagram post"""
        self.logger.info(f"Commenting on Instagram post: {post_url}")
        # Placeholder implementation
        # TODO: Implement actual comment posting
        return ActionResult(success=False, action_type="comment", error="Not implemented")

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        """Comment on an Instagram user's most recent post"""
        self.logger.info(f"Commenting on recent post of Instagram user: {user_id}")
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
