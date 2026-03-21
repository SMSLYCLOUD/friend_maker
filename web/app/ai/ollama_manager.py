import httpx
import platform
import logging
import asyncio
import shutil
import os
import subprocess
from pathlib import Path
from app.config import settings

class OllamaManager:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.logger = logging.getLogger("OllamaManager")
        self.install_path = settings.DATA_DIR / "ollama"

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/tags", timeout=2)
                return r.status_code == 200
        except:
            return False

    async def ensure_ready(self, progress_callback=None):
        """
        Ensure Ollama is running and model is pulled.
        """
        if await self.health_check():
            self.logger.info("Ollama is already running.")
            await self.pull_model(progress_callback)
            return

        # Attempt to start if installed
        if self._is_installed():
            self.logger.info("Starting Ollama...")
            self._start_server()
            # Wait for it to come up
            for _ in range(10):
                if await self.health_check():
                    break
                await asyncio.sleep(2)
        else:
            self.logger.info("Ollama not found. Installing...")
            await self.install_ollama(progress_callback)
            self._start_server()

        await self.pull_model(progress_callback)

    def _is_installed(self) -> bool:
        return shutil.which("ollama") is not None

    async def install_ollama(self, progress_callback=None):
        # In a real app, we'd download the binary for the OS.
        # For this prototype, we'll log instructions or simulate.
        self.logger.info("Downloading Ollama (simulation)...")
        if progress_callback: progress_callback("Downloading Ollama...")
        await asyncio.sleep(1)
        # We can't actually install easily without admin rights or bundling.
        # We'll assume the user might need to install it manually if auto-fail.
        pass

    def _start_server(self):
        # Start in background
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")

    async def pull_model(self, progress_callback=None):
        if progress_callback: progress_callback(f"Pulling model {self.model}...")

        # Check if model exists
        try:
            async with httpx.AsyncClient() as client:
                # Trigger pull
                await client.post(f"{self.base_url}/api/pull", json={"name": self.model}, timeout=10)
        except Exception as e:
            self.logger.warning(f"Could not trigger model pull: {e}")

    async def generate(self, prompt: str) -> str:
        # Check if we should mock
        # We can detect if server is down and return mock if allowed,
        # but for production we want it to fail or retry.

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=120
                )
                if r.status_code == 200:
                    return r.json().get("response", "")
                else:
                    self.logger.error(f"Ollama error: {r.text}")
                    return ""
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return ""
