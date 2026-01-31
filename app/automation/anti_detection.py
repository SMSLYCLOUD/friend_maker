import asyncio
import random
import logging
from datetime import datetime

class AntiDetection:
    def __init__(self):
        self.min_delay = 3.0
        self.max_delay = 12.0
        self.actions_this_session = 0
        self.max_per_session = 25
        self.logger = logging.getLogger("AntiDetection")

    async def random_delay(self):
        """Sleep for a random time to simulate human behavior."""
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.debug(f"Sleeping for {delay:.2f}s")
        await asyncio.sleep(delay)

    def needs_break(self) -> bool:
        return self.actions_this_session >= self.max_per_session

    async def take_break(self):
        """Take a long break."""
        # For testing/demo, we might want shorter breaks, but here is the logic.
        mins = random.randint(15, 45)
        self.logger.info(f"Taking a break for {mins} minutes...")
        await asyncio.sleep(mins * 60)
        self.actions_this_session = 0

    def record_action(self):
        self.actions_this_session += 1
