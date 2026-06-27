import httpx
import logging
from typing import Optional, List

class OpenRouterManager:
    """LLM manager that routes through ProviderManager for multi-provider fallback."""

    def __init__(self):
        self.logger = logging.getLogger("OpenRouterManager")

    def _get_pm(self):
        from app.llm.provider_manager import get_provider_manager
        return get_provider_manager()

    async def health_check(self) -> bool:
        pm = self._get_pm()
        return pm.provider_count > 0

    async def ensure_ready(self, progress_callback=None):
        pm = self._get_pm()
        if progress_callback:
            progress_callback(f"ProviderManager ready with {pm.provider_count} providers.")

    async def generate(self, prompt: str, image_base64: Optional[str] = None, ref_images: Optional[List[str]] = None) -> str:
        pm = self._get_pm()
        provider = pm.get_next_provider()
        if not provider:
            self.logger.error("No LLM providers available")
            return ""

        config = provider.config
        self.logger.info(f"Generating with provider: {config.name}")

        content: list[dict] = [{"type": "text", "text": prompt}]

        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })

        if ref_images:
            for b64 in ref_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })

        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": content}]
        }
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        max_retries = min(4, 1 + pm.provider_count)
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    r = await client.post(
                        f"{config.base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    if r.status_code == 200:
                        data = r.json()
                        choices = data.get("choices", [])
                        if choices:
                            pm.mark_success(config.name)
                            return choices[0].get("message", {}).get("content", "")
                        return ""
                    elif r.status_code == 429:
                        self.logger.warning(f"Rate limited on {config.name} (attempt {attempt+1})")
                        pm.mark_rate_limited(config.name)
                        provider = pm.get_next_provider()
                        if provider:
                            config = provider.config
                            headers["Authorization"] = f"Bearer {config.api_key}"
                            payload["model"] = config.model
                        continue
                    else:
                        self.logger.error(f"LLM error ({r.status_code}) on {config.name}: {r.text[:200]}")
                        pm.mark_failed(config.name)
                        provider = pm.get_next_provider()
                        if provider:
                            config = provider.config
                            headers["Authorization"] = f"Bearer {config.api_key}"
                            payload["model"] = config.model
                        continue
            except Exception as e:
                self.logger.error(f"LLM failed on {config.name}: {e}")
                pm.mark_failed(config.name)
                provider = pm.get_next_provider()
                if provider:
                    config = provider.config
                    headers["Authorization"] = f"Bearer {config.api_key}"
                    payload["model"] = config.model
                continue

        self.logger.error("All providers exhausted for generate()")
        return ""
