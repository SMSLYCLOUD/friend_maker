import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List
from app.database.repository import Repository
from app.automation.executor import CampaignExecutor
from app.platforms.skyvern_adapter import SkyvernAdapter
from app.ai.openrouter_manager import OpenRouterManager
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from app.ai.planner import CampaignPlanner
from app.memory.conversation_memory import get_scheduled_action_manager
from app.config import settings

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
        self.logger.info("Scheduler started (Skyvern AI browser automation).")
        
        # Start scheduled action processor
        self.scheduled_task = asyncio.create_task(self._process_scheduled_actions())

    async def stop(self):
        self.running = False
        # Cancel scheduled action processor
        if hasattr(self, 'scheduled_task'):
            self.scheduled_task.cancel()
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
        self.logger.info("Scheduler stopped.")

    async def start_campaign(self, campaign_id: str, user_id: str):
        if campaign_id in self.tasks:
            self.logger.warning(f"Campaign {campaign_id} already running.")
            return

        self.logger.info(f"Starting campaign {campaign_id}")
        task = asyncio.create_task(self._run_wrapper(campaign_id, user_id))
        self.tasks[campaign_id] = task

    async def stop_campaign(self, campaign_id: str):
        if campaign_id in self.tasks:
            self.tasks[campaign_id].cancel()
            del self.tasks[campaign_id]
            self.logger.info(f"Stopped campaign {campaign_id}")

    async def _run_wrapper(self, campaign_id: str, user_id: str, attempt=1):
        task_repo = Repository()

        try:
            campaign = task_repo.get_campaign(campaign_id, user_id)
            if not campaign:
                self.logger.error(f"Campaign {campaign_id} not found.")
                return

            # Support for multiple account IDs separated by commas for swarm mode
            account_ids = [id.strip() for id in campaign.account_id.split(",")]
            self.logger.info(f"Orchestrating swarm of {len(account_ids)} accounts for mission: {campaign.name}")

            swarm_tasks = []
            for account_id in account_ids:
                swarm_tasks.append(self._run_account_agent(campaign_id, account_id, user_id, task_repo))
            
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
                self.tasks[campaign_id] = asyncio.create_task(self._run_wrapper(campaign_id, user_id, attempt=attempt+1))
        finally:
            task_repo.close()
            if campaign_id in self.tasks and self.tasks[campaign_id] == asyncio.current_task():
                del self.tasks[campaign_id]

    async def _run_account_agent(self, campaign_id: str, account_id: str, user_id: str, repo: Repository):
        """Runs a single agent in the swarm using Skyvern AI browser automation."""
        account = repo.get_account(account_id, user_id)
        if not account:
            self.logger.error(f"Account {account_id} not found. Agent skipped.")
            return

        try:
            adapter = SkyvernAdapter(platform=account.platform)
            executor = CampaignExecutor(repo, adapter, self.classifier, self.generator, self.planner)
            await executor.run_campaign(campaign_id, user_id)

        except Exception as e:
            self.logger.error(f"Swarm Agent [{account.username}] crashed: {e}")

    async def _process_scheduled_actions(self):
        """Background task to process scheduled actions"""
        self.logger.info("Started scheduled action processor")
        while self.running:
            try:
                # Get repository for this background task
                repo = Repository()
                scheduled_manager = get_scheduled_action_manager(repo)
                
                # Get due actions
                current_time = int(datetime.now().timestamp())
                due_actions = await scheduled_manager.get_due_actions(current_time)
                
                for action_info in due_actions:
                    if not self.running:
                        break
                        
                    self.logger.info(f"Processing scheduled action: {action_info['id']} - {action_info['action_type']}")
                    
                    # Create a temporary campaign for this scheduled action
                    # In a full implementation, this would be more integrated
                    try:
                        # Get user info
                        user = repo.get_user(action_info['user_id'])
                        if not user:
                            self.logger.error(f"User not found for scheduled action: {action_info['user_id']}")
                            continue
                            
                        # Get or create a default account for this platform
                        account = repo.get_account_by_user_and_platform(
                            action_info['user_id'], 
                            action_info['platform']
                        )
                        
                        if not account:
                            self.logger.warning(f"No account found for user {action_info['user_id']} on platform {action_info['platform']}")
                            continue
                            
                        # Create a temporary campaign for this action
                        from app.database.models import Campaign
                        temp_campaign = Campaign(
                            id=f"sched_{action_info['id']}",
                            user_id=action_info['user_id'],
                            account_id=account.id,
                            name=f"Scheduled {action_info['action_type']}",
                            campaign_type=action_info['action_type'],
                            status="active",
                            targeting_json=json.dumps({
                                "sources": [action_info['target_user']] if action_info['target_user'] else [],
                                **action_info['parameters']
                            }),
                            message_template=action_info['parameters'].get('message', ''),
                            ai_instructions=action_info['parameters'].get('ai_instructions', ''),
                            schedule_json="{}",
                            daily_limit=1,
                            created_at=current_time
                        )
                        
                        # Execute the campaign (single action) using Skyvern
                        from app.automation.executor import CampaignExecutor
                        from app.platforms.skyvern_adapter import SkyvernAdapter
                        
                        adapter = SkyvernAdapter(platform=account.platform)
                        executor = CampaignExecutor(repo, adapter)
                        await executor.run_campaign(temp_campaign.id, action_info['user_id'])
                            
                    except Exception as e:
                        self.logger.error(f"Error processing scheduled action {action_info['id']}: {e}")
                    finally:
                        # Mark action as completed
                        try:
                            # Calculate next run time based on cron (simplified)
                            # In production, use a proper cron library
                            next_run_time = current_time + 3600  # Default to 1 hour
                            await scheduled_manager.mark_action_completed(
                                action_info['id'], 
                                next_run_time
                            )
                        except Exception as e:
                            self.logger.error(f"Error marking action completed: {e}")
                
                repo.close()
                
            except Exception as e:
                self.logger.error(f"Error in scheduled action processor: {e}")
            
            # Check every 30 seconds
            await asyncio.sleep(30)
