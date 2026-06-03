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

    async def _inter_task_wait(self):
        """Wait the minimum interval between tasks to stay under rate limits."""
        global _last_task_time
        elapsed = time.monotonic() - _last_task_time
        if elapsed < INTER_TASK_DELAY:
            wait = INTER_TASK_DELAY - elapsed
            logger.info(f"Rate-limit guard: sleeping {wait:.0f}s before next task")
            await asyncio.sleep(wait)

    def _to_dict(self, obj) -> dict:
        """Convert an SDK response object to a plain dict."""
        if isinstance(obj, dict):
            return obj
        for method in ("model_dump", "dict"):
            fn = getattr(obj, method, None)
            if fn:
                return fn()
        return vars(obj)

    async def _run_task(self, prompt: str, url: Optional[str] = None, extraction_schema: Optional[dict] = None) -> dict:
        from skyvern import Skyvern
        import asyncio

        pm = _get_provider_manager()
        provider = pm.get_next_provider()
        provider_name = provider.config.name if provider else "default"

        await self._inter_task_wait()
        api_key = os.getenv("SKYVERN_API_KEY", "")
        skyvern = Skyvern(base_url=SKYVERN_BASE_URL, api_key=api_key)
        kwargs: dict[str, Any] = {"prompt": prompt, "wait_for_completion": True, "timeout": 600.0}
        if url:
            kwargs["url"] = url
        if extraction_schema:
            kwargs["data_extraction_schema"] = extraction_schema

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
                result = await skyvern.run_task(**kwargs)
                result = self._to_dict(result)
                logger.info(f"Skyvern task completed: status={result.get('status')}, run_id={result.get('run_id')}")

                _last_task_time = time.monotonic()
                pm.mark_success(provider_name)
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
            home_url = f"https://www.{self.platform}.com"
            prompt = f"Navigate to {home_url}"
            if session_data:
                cookies = json.loads(session_data)
                if isinstance(cookies, list):
                    prompt += f" and inject these cookies: {json.dumps(cookies)}"
                else:
                    prompt += f" and inject this cookie: {json.dumps(cookies)}"
            prompt += ". Check if I am already logged in by looking for a profile icon or avatar."

            task = await self._run_task(prompt=prompt, url=home_url)
            status = task.get("status") if isinstance(task, dict) else getattr(task, "status", "")
            logger.info(f"Authenticate task status: {status}")
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
            task = await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id}/followers and get the first {limit} followers. Return their usernames and display names.",
                url=f"https://www.{self.platform}.com/@{user_id}/followers",
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
                prompt=f"Go to https://www.{self.platform}.com/@{user_id} and click the Follow button.",
                url=f"https://www.{self.platform}.com/@{user_id}",
            )
            return ActionResult(success=True, action_type="follow")
        except Exception as e:
            return ActionResult(success=False, action_type="follow", error=str(e))

    async def unfollow(self, user_id: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id} and click the Following or Unfollow button.",
                url=f"https://www.{self.platform}.com/@{user_id}",
            )
            return ActionResult(success=True, action_type="unfollow")
        except Exception as e:
            return ActionResult(success=False, action_type="unfollow", error=str(e))

    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        try:
            await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id}, open the message or DM button, type '{message}', and send it.",
                url=f"https://www.{self.platform}.com/@{user_id}",
            )
            return ActionResult(success=True, action_type="dm")
        except Exception as e:
            return ActionResult(success=False, action_type="dm", error=str(e))

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

    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            task = await self._run_task(
                prompt=f"Go to https://www.{self.platform}.com/@{user_id} and get the {limit} most recent posts. Return their URLs and captions.",
                url=f"https://www.{self.platform}.com/@{user_id}",
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
                prompt=f"Go to https://www.{self.platform}.com/@{user_id}, find the most recent post, type '{message}' in the comment box, and submit.",
                url=f"https://www.{self.platform}.com/@{user_id}",
            )
            return ActionResult(success=True, action_type="comment")
        except Exception as e:
            return ActionResult(success=False, action_type="comment", error=str(e))

    async def capture_screenshot(self) -> Optional[str]:
        return None
