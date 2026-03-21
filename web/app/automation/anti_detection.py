import asyncio
import random
import logging
from datetime import datetime
from typing import Callable

class AntiDetection:
    def __init__(self):
        self.min_delay = 3.0
        self.max_delay = 12.0
        self.actions_this_session = 0
        self.max_per_session = 25
        self.logger = logging.getLogger("AntiDetection")

    async def _cancellable_sleep(self, seconds: float, is_running: Callable[[], bool]):
        """Sleeps in small chunks to allow immediate cancellation when running is False."""
        slept = 0.0
        chunk = 1.0
        while slept < seconds:
            if not is_running():
                self.logger.info("Sleep interrupted by task cancellation.")
                break
            await asyncio.sleep(min(chunk, seconds - slept))
            slept += chunk

    async def random_delay(self, is_running: Callable[[], bool] = lambda: True):
        """Sleep for a random time to simulate human behavior."""
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.debug(f"Sleeping for {delay:.2f}s")
        await self._cancellable_sleep(delay, is_running)

    def needs_break(self) -> bool:
        return self.actions_this_session >= self.max_per_session

    async def take_break(self, is_running: Callable[[], bool] = lambda: True):
        """Take a long break."""
        # For testing/demo, we might want shorter breaks, but here is the logic.
        mins = random.randint(15, 45)
        self.logger.info(f"Taking a break for {mins} minutes...")
        await self._cancellable_sleep(mins * 60, is_running)
        self.actions_this_session = 0

    async def trigger_cooldown(self, is_running: Callable[[], bool] = lambda: True):
        """Trigger an emergency cool down due to errors."""
        wait_time = 300 # 5 minutes
        self.logger.warning(f"Triggering cooldown for {wait_time}s due to errors...")
        await self._cancellable_sleep(wait_time, is_running)

    def record_action(self):
        self.actions_this_session += 1