"""
Multi-provider LLM manager with rotation and automatic cooldown.

When a provider hits rate limits (429), the manager:
1. Marks it as cooling down
2. Rotates to the next available provider
3. Automatically re-enables after cooldown expires

Providers are configured via environment variables:
  SKYVERN_LLM_PROVIDERS=Groq,OpenRouter,Google,SambaNova
  SKYVERN_LLM_GROQ_API_KEY=gsk_...
  SKYVERN_LLM_GROQ_MODEL=llama-4-scout-17b-16e-instruct
  SKYVERN_LLM_GROQ_BASE_URL=https://api.groq.com/openai/v1
  ...etc for each provider
"""

import os
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str
    rpm_limit: int = 30
    rpd_limit: int = 14400
    supports_vision: bool = True


@dataclass
class ProviderState:
    config: ProviderConfig
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    total_tasks: int = 0
    total_failures: int = 0

    @property
    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    @property
    def cooldown_remaining(self) -> float:
        return max(0.0, self.cooldown_until - time.time())


class ProviderManager:
    """
    Manages multiple LLM providers with rotation and cooldown.

    Usage:
        pm = ProviderManager.from_env()
        provider = pm.get_next_provider()
        # ... use provider ...
        pm.mark_success(provider.name)
        # or on 429:
        pm.mark_rate_limited(provider.name)
        provider = pm.get_next_provider()  # gets next available
    """

    def __init__(self):
        self._providers: list[ProviderState] = []
        self._current_index: int = 0
        self._init_from_env()

    # Default config per provider — only API_KEY required, rest auto-filled
    PROVIDER_DEFAULTS: dict[str, dict] = {
        "Groq": {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "base_url": "https://api.groq.com/openai/v1",
            "rpm_limit": 30,
            "rpd_limit": 14400,
        },
        "OpenRouter": {
            "model": "meta-llama/llama-4-scout:free",
            "base_url": "https://openrouter.ai/api/v1",
            "rpm_limit": 20,
            "rpd_limit": 50,
        },
        "Google": {
            "model": "gemini-2.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "rpm_limit": 10,
            "rpd_limit": 250,
        },
        "SambaNova": {
            "model": "Meta-Llama-4-Scout-17B-16E-Instruct",
            "base_url": "https://api.sambanova.ai/v1",
            "rpm_limit": 30,
            "rpd_limit": 1000,
        },
        "NVIDIA": {
            "model": "meta/llama-4-scout-17b-16e-instruct",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "rpm_limit": 40,
            "rpd_limit": 1000,
        },
    }

    def _init_from_env(self):
        """Parse provider configs from environment variables."""
        provider_names = [
            n.strip()
            for n in os.getenv("SKYVERN_LLM_PROVIDERS", "Groq,OpenRouter").split(",")
            if n.strip()
        ]

        for name in provider_names:
            prefix = f"SKYVERN_LLM_{name.upper().replace(' ', '_')}_"
            defaults = self.PROVIDER_DEFAULTS.get(name, {})

            api_key = os.getenv(f"{prefix}API_KEY", "")
            model = os.getenv(f"{prefix}MODEL", "") or defaults.get("model", "")
            base_url = os.getenv(f"{prefix}BASE_URL", "") or defaults.get("base_url", "")
            rpm_limit = int(os.getenv(f"{prefix}RPM_LIMIT", "") or defaults.get("rpm_limit", 30))
            rpd_limit = int(os.getenv(f"{prefix}RPD_LIMIT", "") or defaults.get("rpd_limit", 14400))
            vision = os.getenv(f"{prefix}VISION", "true").lower() == "true"

            if not api_key:
                logger.warning(f"Provider '{name}' skipped: missing API_KEY")
                continue

            config = ProviderConfig(
                name=name,
                api_key=api_key,
                model=model,
                base_url=base_url,
                rpm_limit=rpm_limit,
                rpd_limit=rpd_limit,
                supports_vision=vision,
            )
            self._providers.append(ProviderState(config=config))
            logger.info(f"Loaded provider: {name} ({model})")

        if not self._providers:
            logger.error("No valid LLM providers configured!")

    def get_next_provider(self) -> Optional[ProviderState]:
        """Get the next available provider, rotating past cooled-down ones."""
        if not self._providers:
            return None

        start = self._current_index
        attempts = 0
        while attempts < len(self._providers):
            provider = self._providers[self._current_index]
            self._current_index = (self._current_index + 1) % len(self._providers)
            attempts += 1

            if provider.is_available:
                return provider

            remaining = provider.cooldown_remaining
            logger.debug(
                f"Provider '{provider.config.name}' cooling down for {remaining:.0f}s"
            )

        # All providers cooling down — return the one with shortest cooldown
        best = min(self._providers, key=lambda p: p.cooldown_remaining)
        if best.cooldown_remaining > 0:
            logger.warning(
                f"All providers cooling down. Fastest available in {best.cooldown_remaining:.0f}s"
            )
        return best

    def mark_success(self, provider_name: str):
        """Mark a provider task as successful."""
        for p in self._providers:
            if p.config.name == provider_name:
                p.consecutive_failures = 0
                p.total_tasks += 1
                logger.debug(f"Provider '{provider_name}' task succeeded")
                return

    def mark_rate_limited(self, provider_name: str, retry_after: Optional[int] = None):
        """Mark a provider as rate-limited with exponential cooldown."""
        for p in self._providers:
            if p.config.name == provider_name:
                p.consecutive_failures += 1
                p.total_failures += 1
                p.total_tasks += 1

                if retry_after:
                    cooldown = retry_after
                else:
                    # Exponential: 60s, 120s, 240s, max 600s
                    cooldown = min(60 * (2 ** (p.consecutive_failures - 1)), 600)

                p.cooldown_until = time.time() + cooldown
                logger.warning(
                    f"Provider '{provider_name}' rate-limited. "
                    f"Cooling down {cooldown}s (attempt {p.consecutive_failures})"
                )
                return

    def mark_failed(self, provider_name: str):
        """Mark a provider task as failed (non-rate-limit)."""
        for p in self._providers:
            if p.config.name == provider_name:
                p.consecutive_failures += 1
                p.total_tasks += 1
                # Short cooldown for general failures
                if p.consecutive_failures >= 3:
                    p.cooldown_until = time.time() + 30
                return

    def get_stats(self) -> dict:
        """Return provider statistics."""
        return {
            p.config.name: {
                "model": p.config.model,
                "available": p.is_available,
                "cooldown_remaining": round(p.cooldown_remaining),
                "consecutive_failures": p.consecutive_failures,
                "total_tasks": p.total_tasks,
                "total_failures": p.total_failures,
            }
            for p in self._providers
        }

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    @property
    def available_count(self) -> int:
        return sum(1 for p in self._providers if p.is_available)


# Singleton
_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
