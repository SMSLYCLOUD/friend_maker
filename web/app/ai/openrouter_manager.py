import httpx
import logging
import asyncio
from app.config import settings

class OpenRouterManager:
    def __init__(self):
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = settings.OPENROUTER_MODEL
        self.api_key = settings.OPENROUTER_API_KEY
        self.logger = logging.getLogger("OpenRouterManager")

    async def health_check(self) -> bool:
        if not self.api_key:
            self.logger.warning("OpenRouter API key is not set.")
            return False

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }
                r = await client.get(f"{self.base_url}/auth/key", headers=headers, timeout=5)
                return r.status_code == 200
        except Exception as e:
            self.logger.error(f"OpenRouter health check failed: {e}")
            return False

    async def ensure_ready(self, progress_callback=None):
        """
        Verify OpenRouter API connectivity and key validity.
        """
        if progress_callback: progress_callback("Checking OpenRouter connection...")

        if not self.api_key:
            self.logger.error("No OpenRouter API key configured.")
            if progress_callback: progress_callback("Error: No OpenRouter API key configured.")
            return

        if await self.health_check():
            self.logger.info("OpenRouter is ready.")
            if progress_callback: progress_callback("OpenRouter connection verified.")
        else:
            self.logger.warning("OpenRouter connection failed or key is invalid.")
            if progress_callback: progress_callback("OpenRouter connection failed.")

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            self.logger.error("Generation failed: OPENROUTER_API_KEY is not set.")
            return ""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=120
                )
                if r.status_code == 200:
                    data = r.json()
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                else:
                    self.logger.error(f"OpenRouter error ({r.status_code}): {r.text}")
                    return ""
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return ""
