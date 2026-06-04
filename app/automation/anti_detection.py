import asyncio
import random
import logging
import math
from datetime import datetime
from typing import Callable, List, Tuple

# Realistic User-Agent strings (2024-2025)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

# Common viewport sizes
VIEWPORTS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (2560, 1440), (1280, 800),
]


class AntiDetection:
    def __init__(self):
        self.min_delay = 30.0
        self.max_delay = 90.0
        self.actions_this_session = 0
        self.max_per_session = 10
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
        mins = random.randint(30, 60)
        self.logger.info(f"Taking a break for {mins} minutes...")
        await self._cancellable_sleep(mins * 60, is_running)
        self.actions_this_session = 0

    async def trigger_cooldown(self, is_running: Callable[[], bool] = lambda: True):
        """Trigger an emergency cool down due to errors."""
        wait_time = 600  # 10 minutes
        self.logger.warning(f"Triggering cooldown for {wait_time}s due to errors...")
        await self._cancellable_sleep(wait_time, is_running)

    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(USER_AGENTS)

    @staticmethod
    def get_random_viewport() -> Tuple[int, int]:
        return random.choice(VIEWPORTS)

    @staticmethod
    def _bezier_curve(start: Tuple[float, float], control1: Tuple[float, float],
                      control2: Tuple[float, float], end: Tuple[float, float],
                      steps: int = 20) -> List[Tuple[float, float]]:
        """Generate a bezier curve for natural mouse movement."""
        points = []
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3 * start[0] + 3*(1-t)**2*t * control1[0] + 3*(1-t)*t**2 * control2[0] + t**3 * end[0]
            y = (1-t)**3 * start[1] + 3*(1-t)**2*t * control1[1] + 3*(1-t)*t**2 * control2[1] + t**3 * end[1]
            points.append((x, y))
        return points

    async def simulate_human_interaction(self, page, is_running: Callable[[], bool] = lambda: True):
        """Simulate random human interactions like scrolling and mouse movements."""
        if not is_running():
            return

        self.logger.debug("Simulating human interaction (scroll and mouse movement)...")

        # Random scrolling with natural acceleration
        for _ in range(random.randint(1, 3)):
            if not is_running():
                return
            scroll_amount = random.randint(100, 500)
            direction = 1 if random.random() > 0.3 else -1  # mostly scroll down
            await page.mouse.wheel(0, scroll_amount * direction)
            await self._cancellable_sleep(random.uniform(0.5, 1.5), is_running)

        # Natural mouse movement using bezier curves
        if is_running():
            start_x = random.randint(100, 800)
            start_y = random.randint(100, 600)
            end_x = random.randint(100, 800)
            end_y = random.randint(100, 600)

            # Control points for natural curve
            ctrl1_x = start_x + random.randint(-200, 200)
            ctrl1_y = start_y + random.randint(-200, 200)
            ctrl2_x = end_x + random.randint(-200, 200)
            ctrl2_y = end_y + random.randint(-200, 200)

            points = self._bezier_curve(
                (start_x, start_y), (ctrl1_x, ctrl1_y),
                (ctrl2_x, ctrl2_y), (end_x, end_y)
            )

            for x, y in points:
                if not is_running():
                    return
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.01, 0.05))

            await self._cancellable_sleep(random.uniform(0.5, 1.0), is_running)

    def record_action(self):
        self.actions_this_session += 1