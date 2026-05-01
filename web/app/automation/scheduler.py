import asyncio
import logging
from typing import Dict
from app.database.repository import Repository
from app.automation.executor import CampaignExecutor
from app.platforms.instagram import InstagramAdapter
from app.ai.openrouter_manager import OpenRouterManager
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from playwright.async_api import async_playwright

class Scheduler:
    def __init__(self):
        self.logger = logging.getLogger("Scheduler")
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}

        self.playwright = None
        self.browser = None

        self.ai_manager = OpenRouterManager()
        self.classifier = ProfileClassifier(self.ai_manager)
        self.generator = MessageGenerator(self.ai_manager)

    async def start(self):
        self.running = True
        self.logger.info("Scheduler started. Launching Playwright browser instance...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def stop(self):
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Scheduler stopped.")

    async def start_campaign(self, campaign_id: str):
        if campaign_id in self.tasks:
            self.logger.warning(f"Campaign {campaign_id} already running.")
            return

        self.logger.info(f"Starting campaign {campaign_id}")
        task = asyncio.create_task(self._run_wrapper(campaign_id))
        self.tasks[campaign_id] = task

    async def stop_campaign(self, campaign_id: str):
        if campaign_id in self.tasks:
            self.tasks[campaign_id].cancel()
            del self.tasks[campaign_id]
            self.logger.info(f"Stopped campaign {campaign_id}")

    async def _run_wrapper(self, campaign_id: str, attempt=1):
        task_repo = Repository()

        try:
            campaign = task_repo.get_campaign(campaign_id)
            if not campaign:
                self.logger.error(f"Campaign {campaign_id} not found.")
                return

            account = task_repo.get_account(campaign.account_id)
            if not account:
                self.logger.error(f"Account for Campaign {campaign_id} not found.")
                return

            if not self.browser:
                self.logger.error("Browser is not initialized.")
                return

            # Create a new context instead of a new browser
            context = await self.browser.new_context()
            page = await context.new_page()

            if account.platform.lower() == "instagram":
                adapter = InstagramAdapter(page)
            elif account.platform.lower() == "twitter":
                from app.platforms.twitter import TwitterAdapter
                adapter = TwitterAdapter(page)
            elif account.platform.lower() == "facebook":
                from app.platforms.facebook import FacebookAdapter
                adapter = FacebookAdapter(page)
            elif account.platform.lower() == "linkedin":
                from app.platforms.linkedin import LinkedInAdapter
                adapter = LinkedInAdapter(page)
            else:
                self.logger.error(f"Platform {account.platform} is not supported.")
                return

            executor = CampaignExecutor(task_repo, adapter, self.classifier, self.generator)
            await executor.run_campaign(campaign_id)

        except asyncio.CancelledError:
            self.logger.info(f"Campaign {campaign_id} task cancelled.")
        except Exception as e:
            self.logger.error(f"Campaign {campaign_id} failed (Attempt {attempt}): {e}")
            if attempt < 3 and self.running:
                self.logger.info(f"Retrying campaign {campaign_id} in 60s...")
                await asyncio.sleep(60)
                # Ensure the previous task is cleaned up before launching a retry task
                if campaign_id in self.tasks:
                    del self.tasks[campaign_id]
                self.tasks[campaign_id] = asyncio.create_task(self._run_wrapper(campaign_id, attempt=attempt+1))
                return # Don't delete the key in finally since we just set it
        finally:
            if 'context' in locals(): await context.close()
            task_repo.close()
            if campaign_id in self.tasks and self.tasks[campaign_id] == asyncio.current_task():
                del self.tasks[campaign_id]
