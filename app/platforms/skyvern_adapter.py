import asyncio
import json
import logging
import os
import time
from typing import Optional, List, Dict, Any

from app.platforms.base import PlatformAdapter, UserProfile, ActionResult

logger = logging.getLogger("SkyvernAdapter")

SKYVERN_BASE_URL = os.getenv("SKYVERN_API_URL", "http://skyvern:8000")
INTER_TASK_DELAY = int(os.getenv("SKYVERN_INTER_TASK_DELAY", "300"))

# Timestamp of last completed Skyvern task (module-level for adapter instances)
_last_task_time: float = 0.0


def _get_provider_manager():
    from app.llm.provider_manager import get_provider_manager
    return get_provider_manager()


class SkyvernAdapter(PlatformAdapter):
    """AI-powered adapter using Skyvern's vision LLMs for all platforms."""

    platform_name: str = "skyvern"

    def __init__(self, platform: str, **kwargs):
        self.platform = platform.lower()
        self.platform_name = platform.lower()
        self._browser_session_id: Optional[str] = None
        self._cookie_header: Optional[str] = None

    async def _ensure_browser_session(self, session_data: Optional[str] = None):
        """Ensure we have a browser session ID for task reuse.
        
        For self-hosted Skyvern, run_task() creates its own browser internally.
        We create a persistent session via the API and pass browser_session_id 
        to run_task() so all tasks in this campaign share the same browser.
        Cookies persist in the browser's profile across tasks.
        
        Each adapter instance = one isolated browser session per account.
        """
        if self._browser_session_id:
            logger.info(f"Reusing browser session: {self._browser_session_id}")
            return

        # Build cookie header from session data for extra_http_headers
        if session_data:
            self._cookie_header = self._get_cookie_header(session_data)
            if self._cookie_header:
                logger.info(f"Built cookie header ({len(self._cookie_header)} chars)")

        from skyvern import Skyvern
        api_key = os.getenv("SKYVERN_API_KEY", "")
        skyvern = Skyvern(base_url=SKYVERN_BASE_URL, api_key=api_key)

        try:
            session = await skyvern.create_browser_session(timeout=60)
            session_dict = self._to_dict(session)
            self._browser_session_id = session_dict.get("browser_session_id") or session_dict.get("id")
            logger.info(f"Created browser session: {self._browser_session_id}")
        except Exception as e:
            logger.warning(f"Failed to create browser session: {e}")
            self._browser_session_id = None

    async def _inter_task_wait(self):
        """Wait the minimum interval between tasks to stay under rate limits."""
        global _last_task_time
        elapsed = time.monotonic() - _last_task_time
        if elapsed < INTER_TASK_DELAY:
            wait = INTER_TASK_DELAY - elapsed
            logger.info(f"Rate-limit guard: sleeping {wait:.0f}s before next task")
            await asyncio.sleep(wait)

    async def _run_task_with_extraction(
        self, prompt: str, url: str, extraction_goal: str, extraction_schema: dict,
        poll_interval: float = 5.0, timeout: float = 600.0
    ) -> dict:
        """Run a Skyvern task via httpx directly, passing data_extraction_goal + schema."""
        import httpx as httpx_mod

        await self._inter_task_wait()
        api_key = os.getenv("SKYVERN_API_KEY", "")

        payload = {
            "prompt": prompt,
            "url": url,
            "data_extraction_goal": extraction_goal,
            "data_extraction_schema": extraction_schema,
            "wait_for_completion": False,
            "max_screenshot_scrolls": 5,
        }
        if self._browser_session_id:
            payload["browser_session_id"] = self._browser_session_id
        if self._cookie_header:
            payload["extra_http_headers"] = {"Cookie": self._cookie_header}
        proxy_config = self._get_proxy_config()
        if proxy_config:
            payload["proxy"] = proxy_config
            logger.info(f"Using proxy for extraction: {proxy_config['url'][:30]}...")

        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        async with httpx_mod.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{SKYVERN_BASE_URL}/v1/run/tasks", json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            run_id = result.get("run_id")
            logger.info(f"Extraction task created: {run_id}")

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                await asyncio.sleep(poll_interval)
                poll_resp = await client.get(f"{SKYVERN_BASE_URL}/v1/runs/{run_id}", headers=headers)
                poll_resp.raise_for_status()
                result = poll_resp.json()
                status = result.get("status", "unknown")
                if status in ("completed", "failed", "terminated", "timed_out", "canceled"):
                    break

        _last_task_time = time.monotonic()
        logger.info(f"Extraction task done: status={status}, output={'present' if result.get('output') else 'null'}")

        # Retry once if output is null (likely Groq 413 — screenshots too large)
        if not result.get("output") and status == "completed":
            logger.warning("Extraction returned null output — retrying once after 10s (suspected LLM provider failure)")
            await asyncio.sleep(10)
            async with httpx_mod.AsyncClient(timeout=30) as retry_client:
                retry_resp = await retry_client.post(f"{SKYVERN_BASE_URL}/v1/run/tasks", json=payload, headers=headers)
                retry_resp.raise_for_status()
                retry_result = retry_resp.json()
                retry_run_id = retry_result.get("run_id")
                logger.info(f"Retry extraction task created: {retry_run_id}")
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    await asyncio.sleep(poll_interval)
                    poll_resp = await retry_client.get(f"{SKYVERN_BASE_URL}/v1/runs/{retry_run_id}", headers=headers)
                    poll_resp.raise_for_status()
                    retry_result = poll_resp.json()
                    retry_status = retry_result.get("status", "unknown")
                    if retry_status in ("completed", "failed", "terminated", "timed_out", "canceled"):
                        break
                _last_task_time = time.monotonic()
                if retry_result.get("output"):
                    logger.info(f"Retry extraction succeeded: status={retry_status}")
                    return retry_result
                logger.warning(f"Retry extraction also null: status={retry_status}")

        return result

    def _to_dict(self, obj) -> dict:
        """Convert an SDK response object to a plain dict."""
        if isinstance(obj, dict):
            return obj
        for method in ("model_dump", "dict"):
            fn = getattr(obj, method, None)
            if fn:
                return fn()
        return vars(obj)

    @staticmethod
    def _get_proxy_config() -> Optional[dict]:
        """Build proxy config from environment variables for Skyvern."""
        url = os.getenv("SKYVERN_PROXY_URL", "").strip()
        if not url:
            return None
        username = os.getenv("SKYVERN_PROXY_USERNAME", "").strip()
        password = os.getenv("SKYVERN_PROXY_PASSWORD", "").strip()
        proxy: dict[str, str] = {"url": url}
        if username:
            proxy["username"] = username
        if password:
            proxy["password"] = password
        return proxy

    async def _run_task(self, prompt: str, url: Optional[str] = None, extraction_schema: Optional[dict] = None) -> dict:
        import httpx as httpx_mod
        import asyncio

        pm = _get_provider_manager()
        provider = pm.get_next_provider()
        provider_name = provider.config.name if provider else "default"

        await self._inter_task_wait()
        api_key = os.getenv("SKYVERN_API_KEY", "")
        proxy_config = self._get_proxy_config()

        payload: dict[str, Any] = {
            "prompt": prompt,
            "wait_for_completion": False,
        }
        if url:
            payload["url"] = url
        if extraction_schema:
            payload["data_extraction_schema"] = extraction_schema
        if self._browser_session_id:
            payload["browser_session_id"] = self._browser_session_id
            logger.info(f"Using browser session: {self._browser_session_id}")
        else:
            logger.warning("No browser session ID set - task will use fresh browser (may fail for logged-in pages)")
        if self._cookie_header:
            payload["extra_http_headers"] = {"Cookie": self._cookie_header}
            logger.info(f"Passing cookie header ({len(self._cookie_header)} chars)")
        if proxy_config:
            payload["proxy"] = proxy_config
            logger.info(f"Using proxy: {proxy_config['url'][:30]}...")

        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        max_retries = min(6, 2 + pm.provider_count)
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = min(60 * (2 ** (attempt - 1)), 600)
                    provider = pm.get_next_provider()
                    provider_name = provider.config.name if provider else "default"
                    logger.info(
                        f"Retry attempt {attempt}/{max_retries} with provider '{provider_name}' "
                        f"after {delay}s delay"
                    )
                    await asyncio.sleep(delay)

                logger.info(f"Running Skyvern task with provider '{provider_name}': {prompt[:80]}...")

                async with httpx_mod.AsyncClient(timeout=30) as client:
                    resp = await client.post(f"{SKYVERN_BASE_URL}/v1/run/tasks", json=payload, headers=headers)
                    resp.raise_for_status()
                    result = resp.json()
                    run_id = result.get("run_id")

                    deadline = time.monotonic() + 600.0
                    while time.monotonic() < deadline:
                        await asyncio.sleep(5)
                        poll_resp = await client.get(f"{SKYVERN_BASE_URL}/v1/runs/{run_id}", headers=headers)
                        poll_resp.raise_for_status()
                        result = poll_resp.json()
                        status = result.get("status", "unknown")
                        if status in ("completed", "failed", "terminated", "timed_out", "canceled"):
                            break

                _last_task_time = time.monotonic()
                status = result.get("status", "unknown")
                output = result.get("output", {})
                logger.info(f"Skyvern task completed: status={status}, run_id={run_id}, output_keys={list(output.keys()) if isinstance(output, dict) else 'N/A'}")

                pm.mark_success(provider_name)

                if status == "failed":
                    error_msg = result.get("error", "Skyvern task failed")
                    logger.error(f"Skyvern task FAILED: status={status}, run_id={run_id}, error={error_msg}")
                    raise Exception(f"Skyvern task failed: {error_msg}")

                if status == "terminated" and not output:
                    failure_reason = result.get("failure_reason", "")
                    logger.warning(f"Skyvern task terminated: run_id={run_id}, reason={failure_reason}")
                    # Don't raise — terminated is a valid end state for some tasks (e.g. auth check)

                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_rate_limit = (
                    "429" in error_str
                    or "rate" in error_str
                    or "ratelimit" in error_str
                    or "too many requests" in error_str
                    or "quota" in error_str
                )
                if is_rate_limit:
                    logger.warning(
                        f"Rate limited on attempt {attempt + 1} "
                        f"(provider: {provider_name})"
                    )
                    pm.mark_rate_limited(provider_name)
                    continue

                pm.mark_failed(provider_name)
                raise

        raise last_error or Exception("All retry attempts exhausted")

    async def authenticate(
        self,
        session_data: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        try:
            await self._ensure_browser_session(session_data)

            home_url = f"https://www.{self.platform}.com"

            prompt = (
                f"Navigate to {home_url} and check if I am logged in. "
                f"Look for a profile icon, avatar, or username in the navigation bar. "
                f"Do NOT click any login or sign-up buttons. "
                f"Do NOT terminate early. "
                f"Report whether I am logged in or not."
            )

            task = await self._run_task(prompt=prompt, url=home_url)
            status = task.get("status") if isinstance(task, dict) else getattr(task, "status", "")
            output = task.get("output") if isinstance(task, dict) else getattr(task, "output", None)
            logger.info(f"Authenticate task status: {status}, output: {output}")
            return status in ("completed", "created", "terminated")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def search_users(self, query: str, limit: int = 20, context: str = "") -> List[UserProfile]:
        results = []
        try:
            context_line = f"\n\nTARGET AUDIENCE: {context}" if context else ""
            prompt = f"Go to https://www.{self.platform}.com/search?q={query} and find the first {limit} user profiles that match the target audience. Return their usernames and display names.{context_line}"
            task = await self._run_task(
                prompt=prompt,
                url=f"https://www.{self.platform}.com/search?q={query}",
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            users = data.get("users", []) if isinstance(data, dict) else []
            for item in users[:limit]:
                results.append(
                    UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    )
                )
        except Exception as e:
            logger.error(f"Search users on {self.platform} failed: {e}")
        return results

    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            handle = user_id.lstrip("@")
            url = f"https://www.{self.platform}.com/@{handle}"
            task = await self._run_task_with_extraction(
                prompt=(
                    f"Go to the profile page for @{handle} on {self.platform}. "
                    f"Find and open the followers list, then extract the usernames and display names "
                    f"of the first {limit} followers."
                ),
                url=url,
                extraction_goal=f"Extract the usernames and display names of the first {limit} followers from the followers list",
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            users = data.get("users", []) if isinstance(data, dict) else []
            for item in users[:limit]:
                results.append(
                    UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    )
                )
        except Exception as e:
            logger.error(f"Get followers on {self.platform} failed: {e}")
        return results

    async def follow(self, user_id: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id.lstrip("@")} and click the Follow button.",
                url=f"https://www.{self.platform}.com/@{user_id.lstrip("@")}",
            )
            return ActionResult(success=True, action_type="follow")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id.lstrip("@")} and click the Following or Unfollow button.",
                url=f"https://www.{self.platform}.com/@{user_id.lstrip("@")}",
            )
            return ActionResult(success=True, action_type="unfollow")
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id.lstrip("@")}, open the message or DM button, type '{message}', and send it.",
                url=f"https://www.{self.platform}.com/@{user_id.lstrip("@")}",
            )
            return ActionResult(success=True, action_type="dm")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

    async def check_inbox(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Check DM inbox for unread messages. Returns list of conversations with new messages."""
        try:
            task = await self._run_task(
                prompt=(
                    f"Go to your DM inbox on {self.platform}. "
                    f"Find conversations that have UNREAD messages (new messages from others that you haven't opened yet). "
                    f"For each unread conversation, extract: "
                    f"1. The username of the person who messaged you "
                    f"2. The content of their latest message "
                    f"3. How many unread messages there are "
                    f"Return up to {limit} unread conversations."
                ),
                url=f"https://www.{self.platform}.com/direct/inbox",
                extraction_schema={
                    "type": "object",
                    "properties": {
                        "unread_conversations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "latest_message": {"type": "string"},
                                    "unread_count": {"type": "integer"},
                                },
                            },
                        }
                    },
                },
            )
            data = task.get("output", {})
            convos = data.get("unread_conversations", []) if isinstance(data, dict) else []
            logger.info(f"Inbox check: found {len(convos)} unread conversations")
            return convos[:limit]
        except Exception as e:
            logger.error(f"Inbox check failed: {e}")
            return []

    async def read_conversation(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Read the last N messages in a DM conversation with a specific user."""
        handle = user_id.lstrip("@")
        try:
            task = await self._run_task(
                prompt=(
                    f"Go to your DM conversation with @{handle} on {self.platform}. "
                    f"Read the last {limit} messages in the conversation. "
                    f"For each message, extract: "
                    f"1. Who sent it (\"me\" or \"{handle}\") "
                    f"2. The message content "
                    f"Return the messages in chronological order (oldest first)."
                ),
                url=f"https://www.{self.platform}.com/direct/t/{handle}",
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            messages = data.get("messages", []) if isinstance(data, dict) else []
            logger.info(f"Read conversation with @{handle}: {len(messages)} messages")
            return messages[:limit]
        except Exception as e:
            logger.error(f"Read conversation with @{handle} failed: {e}")
            return []

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        results = []
        try:
            task = await self._run_task(
                prompt=f"Go to {group_id} and get the first {limit} members. Return their usernames and display names.",
                url=group_id,
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            users = data.get("users", []) if isinstance(data, dict) else []
            for item in users[:limit]:
                results.append(
                    UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    )
                )
        except Exception as e:
            logger.error(f"Get group members on {self.platform} failed: {e}")
        return results

    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        results = []
        try:
            task = await self._run_task(
                prompt=f"Go to {post_url} and get the first {limit} users who commented. Return their usernames and display names.",
                url=post_url,
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            users = data.get("users", []) if isinstance(data, dict) else []
            for item in users[:limit]:
                results.append(
                    UserProfile(
                        platform_id=item.get("username", ""),
                        username=item.get("username", ""),
                        display_name=item.get("display_name"),
                    )
                )
        except Exception as e:
            logger.error(f"Get post commenters on {self.platform} failed: {e}")
        return results

    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            task = await self._run_task(
                prompt=f"Go to {post_url} and get the first {limit} comments. For each, return the author username and comment text.",
                url=post_url,
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            comments = data.get("comments", []) if isinstance(data, dict) else []
            return comments[:limit]
        except Exception as e:
            logger.error(f"Get post comments on {self.platform} failed: {e}")
            return []

    async def reply_to_comment(self, comment_id: str, message: str, post_url: Optional[str] = None) -> ActionResult:
        try:
            prompt = f"Reply '{message}' to the comment by user '{comment_id}'"
            url = post_url
            if url:
                prompt += f" on the post at {url}"
            prompt += ". Find the comment in the comment thread, click the reply button, type the message, and submit it."
            await self._run_task(prompt=prompt, url=url)
            return ActionResult(success=True, action_type="reply_comment")
        except Exception as e:
            return ActionResult(success=False, action_type="reply_comment", error=str(e))

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Scrape a user's profile page for bio, recent posts, and screenshot."""
        handle = user_id.lstrip("@")
        url = f"https://www.{self.platform}.com/@{handle}"
        try:
            task = await self._run_task(
                prompt=(
                    f"Go to {url} and extract the following from this user's profile:\n"
                    f"1. Their bio/description text\n"
                    f"2. Their display name\n"
                    f"3. Their follower count\n"
                    f"4. Their 3 most recent post captions\n"
                    f"Return all of this information."
                ),
                url=url,
                extraction_schema={
                    "type": "object",
                    "properties": {
                        "bio": {"type": "string"},
                        "display_name": {"type": "string"},
                        "follower_count": {"type": "string"},
                        "recent_posts": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            )
            data = task.get("output", {})
            if not isinstance(data, dict):
                data = {}
            return {
                "username": handle,
                "bio": data.get("bio", ""),
                "display_name": data.get("display_name", ""),
                "follower_count": data.get("follower_count", ""),
                "recent_posts": data.get("recent_posts", []),
            }
        except Exception as e:
            logger.error(f"Get user profile on {self.platform} failed: {e}")
            return {"username": handle, "bio": "", "display_name": "", "follower_count": "", "recent_posts": []}

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            task = await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id.lstrip("@")} and get the {limit} most recent posts. Return their URLs and captions.",
                url=f"https://www.{self.platform}.com/@{user_id.lstrip("@")}",
                extraction_schema={
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
                },
            )
            data = task.get("output", {})
            posts = data.get("posts", []) if isinstance(data, dict) else []
            return posts[:limit]
        except Exception as e:
            logger.error(f"Get recent posts on {self.platform} failed: {e}")
            return []

    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to {post_url} and type the comment '{message}' in the comment box, then submit it.",
                url=post_url,
            )
            return ActionResult(success=True, action_type="comment")
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id.lstrip("@")}, find the most recent post, type '{message}' in the comment box, and submit.",
                url=f"https://www.{self.platform}.com/@{user_id.lstrip("@")}",
            )
            return ActionResult(success=True, action_type="comment")
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def capture_screenshot(self) -> Optional[str]:
        """Screenshot not supported via Skyvern task API. Returns None."""
        return None
