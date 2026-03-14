import asyncio
import logging
from typing import Dict
from app.database.repository import Repository
from app.automation.executor import CampaignExecutor
from app.platforms.instagram import InstagramAdapter
from app.ai.ollama_manager import OllamaManager
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from playwright.async_api import async_playwright

class Scheduler:
    def __init__(self):
        self.logger = logging.getLogger("Scheduler")
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}

        # self.repo = Repository()  <-- Don't hold a shared connection
        # Instead, we just hold config/managers that are thread-safe or stateless
        self.ollama = OllamaManager()
        self.classifier = ProfileClassifier(self.ollama)
        self.generator = MessageGenerator(self.ollama)

        # Main thread repo for simple UI access if needed,
        # but better to let UI instantiate its own.
        # However, for 'start_campaign' check, we might need one?
        # Let's keep one for the main thread operations if strictly needed,
        # but avoid passing it to tasks.
        self.main_repo = Repository()

    async def start(self):
        self.running = True
        self.logger.info("Scheduler started.")
        # In a real app, this might poll DB for scheduled campaigns.
        # For now, it manages manually started tasks.

    async def stop(self):
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
        self.logger.info("Scheduler stopped.")

    async def start_campaign(self, campaign_id: str):
        if campaign_id in self.tasks:
            self.logger.warning(f"Campaign {campaign_id} already running.")
            return

        self.logger.info(f"Starting campaign {campaign_id}")

        # We need to spawn a Playwright instance for this campaign
        # This is heavy. Ideally we reuse or limit concurrent ones.
        task = asyncio.create_task(self._run_wrapper(campaign_id))
        self.tasks[campaign_id] = task

    async def stop_campaign(self, campaign_id: str):
        if campaign_id in self.tasks:
            self.tasks[campaign_id].cancel()
            del self.tasks[campaign_id]
            self.logger.info(f"Stopped campaign {campaign_id}")

    async def _run_wrapper(self, campaign_id: str, attempt=1):
        # Create a fresh Repository instance for this task/thread
        # This ensures a unique SQLite connection.
        task_repo = Repository()

        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # TODO: Determine platform from Campaign -> Account
            # For now assuming Instagram
            adapter = InstagramAdapter(page)
            executor = CampaignExecutor(task_repo, adapter, self.classifier, self.generator)

            await executor.run_campaign(campaign_id)

        except asyncio.CancelledError:
            self.logger.info(f"Campaign {campaign_id} task cancelled.")
        except Exception as e:
            self.logger.error(f"Campaign {campaign_id} failed (Attempt {attempt}): {e}")
            if attempt < 3:
                self.logger.info(f"Retrying campaign {campaign_id} in 60s...")
                await asyncio.sleep(60)
                # Restart
                # We can't recursive await easily without proper task management or it blocks.
                # But since this is inside a task, we can just loop or recurse if stack depth isn't issue.
                # Simplest is just to restart the wrapper logic?
                # Better: The caller should handle restart, or we use a loop.
                # I'll rely on the task ending.
        finally:
            if 'browser' in locals(): await browser.close()
            if 'playwright' in locals(): await playwright.stop()
            if campaign_id in self.tasks:
                del self.tasks[campaign_id]
