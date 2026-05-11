import asyncio
import logging
from typing import Optional
from app.database.repository import Repository
from app.database.models import Campaign, Target, ActionLog
from app.platforms.base import PlatformAdapter
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from app.ai.planner import CampaignPlanner
from app.automation.anti_detection import AntiDetection

class CampaignExecutor:
    def __init__(self,
                 repository: Repository,
                 adapter: PlatformAdapter,
                 classifier: Optional[ProfileClassifier] = None,
                 generator: Optional[MessageGenerator] = None,
                 planner: Optional[CampaignPlanner] = None):
        self.repo = repository
        self.adapter = adapter
        self.classifier = classifier
        self.generator = generator
        self.planner = planner
        self.anti_detect = AntiDetection()
        self.logger = logging.getLogger(f"Executor-{adapter.platform_name}")
        self.running = False

    async def run_campaign(self, campaign_id: str):
        self.running = True
        campaign = self.repo.get_campaign(campaign_id)
        if not campaign:
            self.logger.error("Campaign not found")
            return

        self.logger.info(f"Starting campaign: {campaign.name}")

        # 1. Authenticate
        account = self.repo.get_account(campaign.account_id)
        if not account:
            self.logger.error("Account not found")
            return

        if not await self.adapter.authenticate(account.session_data, account.username, account.password):
            self.logger.error("Authentication failed. Aborting.")
            return

        actions_today = 0
        limit = campaign.daily_limit or 50

        while self.running:
            if actions_today >= limit:
                self.logger.info(f"Daily limit of {limit} reached. Pausing until tomorrow.")
                # Basic implementation: stop execution. A real task queue would reschedule for tomorrow.
                self.running = False
                break

            if self.anti_detect.needs_break():
                await self.anti_detect.take_break(lambda: self.running)

            if not self.running: break

            # 2. Get pending targets or fetch new ones
            pending = self.repo.get_pending_targets(campaign_id, limit=1)

            if not pending:
                self.logger.info("No pending targets. Fetching new ones...")
                await self._fetch_new_targets(campaign)
                pending = self.repo.get_pending_targets(campaign_id, limit=1)
                if not pending:
                    self.logger.info("Could not find new targets. Stopping.")
                    break

            target = pending[0]
            try:
                await self._process_target(target, campaign)
                actions_today += 1
                await self.anti_detect.random_delay(lambda: self.running)
            except asyncio.CancelledError:
                self.logger.info("Task cancelled during target processing.")
                raise
            except Exception as e:
                self.logger.error(f"Error processing target {target.username}: {e}")
                # Log failure
                self.repo.log_action(ActionLog(
                    id=f"log_fail_{target.id}_{int(asyncio.get_event_loop().time())}",
                    account_id=campaign.account_id,
                    campaign_id=campaign.id,
                    action_type="unknown",
                    target_user=target.username,
                    success=False,
                    error=str(e)
                ))
                self.repo.update_target_status(target.id, "failed")

                # Trigger cooldown
                await self.anti_detect.trigger_cooldown(lambda: self.running)

        self.logger.info("Campaign execution stopped.")

    async def _fetch_new_targets(self, campaign: Campaign):
        """Search for or discover users based on campaign targeting settings."""
        targeting = campaign.targeting
        
        # 1. Check if we need AI Strategic Planning
        if not targeting.get("sources") and self.planner and campaign.ai_instructions:
            self.logger.info("No sources defined. Triggering AI Strategic Planning...")
            plan = await self.planner.generate_discovery_plan(
                campaign.ai_instructions, 
                self.adapter.platform_name
            )
            
            # Enrich targeting with AI-generated plan
            # We map target_accounts to 'follower_mining' sources and keywords to 'search'
            sources = plan.get("keywords", []) + plan.get("target_accounts", [])
            strategy = "follower_mining" if plan.get("target_accounts") else "search"
            
            # Update campaign targeting for persistence
            targeting["sources"] = sources
            targeting["strategy"] = strategy
            import json
            campaign.targeting_json = json.dumps(targeting)
            self.repo.update_campaign(campaign)
            
            self.logger.info(f"AI Plan Generated: {len(sources)} strategic sources identified.")

        strategy = targeting.get("strategy", "search")
        sources = targeting.get("sources", [])
        
        if not sources and "tags" in targeting:
            sources = targeting.get("tags", [])

        self.logger.info(f"Executing discovery strategy: {strategy} across {len(sources)} sources")

        users = []
        for source in sources:
            if not self.running: break
            
            self.logger.info(f"Combing source: {source}")
            
            try:
                if strategy == "search":
                    new_users = await self.adapter.search_users(source, limit=10)
                elif strategy == "group_combing":
                    new_users = await self.adapter.get_group_members(source, limit=20)
                elif strategy == "post_auditing":
                    new_users = await self.adapter.get_post_commenters(source, limit=20)
                elif strategy == "follower_mining":
                    new_users = await self.adapter.get_followers(source, limit=20)
                else:
                    self.logger.warning(f"Unknown discovery strategy: {strategy}")
                    new_users = []
                
                users.extend(new_users)
            except Exception as e:
                self.logger.error(f"Failed to comb {source}: {e}")

        for u in users:
            # Add to DB
            t = Target(
                id=f"{campaign.id}_{u.platform_id}",
                campaign_id=campaign.id,
                platform_user_id=u.platform_id,
                username=u.username,
                status="pending"
            )
            self.repo.add_target(t)

    async def _process_target(self, target: Target, campaign: Campaign):
        self.logger.info(f"Processing target: {target.username}")

        # 0. Capture Vision (Optional but recommended for 'eyes')
        image_base64 = await self.adapter.capture_screenshot()

        # 1. Analyze (AI)
        if self.classifier:
            profile_data = {"username": target.username, "bio": "Fetched bio..."}
            analysis = await self.classifier.classify(profile_data, image_base64=image_base64)
            score = analysis.get("match_score", 0.0)

            if score < 0.5: # Threshold
                self.repo.update_target_status(target.id, "skipped_low_score", ai_score=score)
                return

            self.repo.update_target_status(target.id, "analyzed", ai_score=score)

        # 2. Action (Follow/DM)
        action_type = campaign.campaign_type # e.g. "outreach", "growth"

        success = False
        error = None

        if action_type == "growth":
            res = await self.adapter.follow(target.platform_user_id)
            success = res.success
            error = res.error
        elif action_type == "outreach":
            msg = "Hello!"
            if self.generator:
                msg = await self.generator.generate_dm(
                    {"username": target.username}, 
                    campaign.message_template, 
                    campaign.ai_instructions,
                    image_base64=image_base64
                )
            res = await self.adapter.send_dm(target.platform_user_id, msg)
            success = res.success
            error = res.error

        # 3. Log
        self.repo.log_action(ActionLog(
            id=f"log_{target.id}_{int(asyncio.get_event_loop().time())}",
            account_id=campaign.account_id,
            campaign_id=campaign.id,
            action_type=action_type,
            target_user=target.username,
            success=success,
            error=error
        ))

        self.repo.update_target_status(target.id, "completed" if success else "failed")
        self.anti_detect.record_action()

    def stop(self):
        self.running = False
