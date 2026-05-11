import asyncio
import logging
from typing import Dict
from app.database.repository import Repository
from app.automation.executor import CampaignExecutor
from app.platforms.instagram import InstagramAdapter
from app.ai.openrouter_manager import OpenRouterManager
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from app.ai.planner import CampaignPlanner
from app.config import settings
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
        self.planner = CampaignPlanner(self.ai_manager)

    async def start(self):
        self.running = True
        if not settings.USE_ANDROID_EMULATOR:
            self.logger.info("Scheduler started. Launching Playwright browser instance...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
        else:
            self.logger.info("Scheduler started. Playwright skipped (Using Android Emulator).")

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

            # Support for multiple account IDs separated by commas for swarm mode
            account_ids = [id.strip() for id in campaign.account_id.split(",")]
            self.logger.info(f"Orchestrating swarm of {len(account_ids)} accounts for mission: {campaign.name}")

            swarm_tasks = []
            for account_id in account_ids:
                swarm_tasks.append(self._run_account_agent(campaign_id, account_id, task_repo))
            
            await asyncio.gather(*swarm_tasks)

        except asyncio.CancelledError:
            self.logger.info(f"Campaign {campaign_id} swarm mission cancelled.")
        except Exception as e:
            self.logger.error(f"Campaign {campaign_id} swarm failed (Attempt {attempt}): {e}")
            if attempt < 3 and self.running:
                self.logger.info(f"Retrying swarm mission {campaign_id} in 60s...")
                await asyncio.sleep(60)
                if campaign_id in self.tasks:
                    del self.tasks[campaign_id]
                self.tasks[campaign_id] = asyncio.create_task(self._run_wrapper(campaign_id, attempt=attempt+1))
        finally:
            task_repo.close()
            if campaign_id in self.tasks and self.tasks[campaign_id] == asyncio.current_task():
                del self.tasks[campaign_id]

    async def _run_account_agent(self, campaign_id: str, account_id: str, repo: Repository):
        """Runs a single agent in the swarm."""
        account = repo.get_account(account_id)
        if not account:
            self.logger.error(f"Account {account_id} not found. Agent skipped.")
            return

        context = None
        try:
            from app.platforms.android_app import AndroidAppAdapter
            
            if settings.USE_ANDROID_EMULATOR:
                self.logger.info(f"Swarm Agent [{account.username}] using Android Emulator.")
                adapter = AndroidAppAdapter(account.platform)
            else:
                if not self.browser:
                    self.logger.error("Browser is not initialized.")
                    return

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
                elif account.platform.lower() == "tiktok":
                    from app.platforms.tiktok import TiktokAdapter
                    adapter = TiktokAdapter(page)
                else:
                    self.logger.error(f"Platform {account.platform} not supported for swarm agent.")
                    return

            executor = CampaignExecutor(repo, adapter, self.classifier, self.generator, self.planner)
            await executor.run_campaign(campaign_id)

        except Exception as e:
            self.logger.error(f"Swarm Agent [{account.username}] crashed: {e}")
        finally:
            if context: await context.close()
