import asyncio
import logging
import json
from typing import List, Optional
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
                await self.page.goto("https://www.instagram.com/accounts/login/", timeout=30000)
                await self.page.wait_for_load_state("networkidle", timeout=15000)

                # Wait for login form to appear (IG is SPA, form loads dynamically)
                try:
                    await self.page.wait_for_selector('form[action*="login"]', timeout=10000)
                except Exception:
                    self.logger.warning("Form not found, trying alternate wait...")

                username_selectors = [
                    'input[name="username"]',
                    'input[data-testid="cookie-user-credential-yellow-foreground-input"]',
                ]
                for sel in username_selectors:
                    if await self.page.locator(sel).count() > 0:
                        await self.page.locator(sel).first.fill(username)
                        break
                else:
                    # Fallback: try XPath
                    try:
                        await self.page.locator('xpath=//input[@name="username"]').fill(username)
                    except Exception:
                        self.logger.error("Could not find username field.")
                        return False

                await self.page.wait_for_timeout(500)

                # Look for Next or Continue button, then password
                for btn_sel in ['button:has-text("Next")', 'button:has-text("Continue")']:
                    if await self.page.locator(btn_sel).count() > 0:
                        await self.page.locator(btn_sel).first.click()
                        await self.page.wait_for_timeout(1000)
                        break

                password_selectors = [
                    'input[name="password"]',
                ]
                for sel in password_selectors:
                    if await self.page.locator(sel).count() > 0:
                        await self.page.locator(sel).first.fill(password)
                        break
                else:
                    try:
                        await self.page.locator('xpath=//input[@name="password"]').fill(password)
                    except Exception:
                        self.logger.error("Could not find password field.")
                        return False

                await self.page.wait_for_timeout(500)

                login_btns = [
                    'button[type="submit"]:has-text("Log in")',
                    'button[type="submit"]:has-text("Log in ")',
                    'button:has-text("Log in")',
                ]
                for sel in login_btns:
                    if await self.page.locator(sel).count() > 0:
                        await self.page.locator(sel).first.click()
                        break

                try:
                    await self.page.wait_for_selector('svg[aria-label="New post"]', timeout=15000)
                    return True
                except:
                    # Save screenshot for debugging
                    try:
                        await self.page.screenshot(path="/tmp/ig_login_debug.png")
                        self.logger.error("Debug screenshot saved to /tmp/ig_login_debug.png")
                    except:
                        pass
                    self.logger.error("Login failed — Instagram may require verification or credentials changed.")
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

    async def capture_screenshot(self) -> Optional[str]:
        try:
            screenshot_bytes = await self.page.screenshot(type="jpeg", quality=80)
            import base64
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            return None
