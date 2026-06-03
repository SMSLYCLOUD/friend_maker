import asyncio
import logging
import json
import os
import base64
from typing import Optional, List, Dict, Any
from app.database.repository import Repository
from app.database.models import Campaign, Target, ActionLog
from app.platforms.base import PlatformAdapter
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator
from app.ai.planner import CampaignPlanner
from app.automation.anti_detection import AntiDetection
from app.memory.conversation_memory import get_conversation_memory, get_relationship_tracker, get_scheduled_action_manager

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
        # Initialize memory systems
        self.conversation_memory = get_conversation_memory(repository)
        self.relationship_tracker = get_relationship_tracker(repository)
        self.scheduled_action_manager = get_scheduled_action_manager(repository)
        self.logger = logging.getLogger(f"Executor-{adapter.platform_name}")
        self.running = False
        self.bot_instructions = ""

    def load_bot_instructions(self):
        self.bot_instructions = self.repo.get_global_setting("BOT_INSTRUCTIONS", "")
        if self.bot_instructions:
            self.logger.info(f"Loaded bot instructions ({len(self.bot_instructions)} chars)")

    def load_reference_images(self) -> List[str]:
        raw = self.repo.get_global_setting("BOT_INSTRUCTION_IMAGES", "[]")
        try:
            filenames = json.loads(raw)
        except:
            return []
        images = []
        for f in filenames:
            path = os.path.join("uploads/bot_images", f)
            if os.path.exists(path):
                with open(path, "rb") as img:
                    b64 = base64.b64encode(img.read()).decode()
                    images.append(b64)
        if images:
            self.logger.info(f"Loaded {len(images)} reference images")
        return images

    async def run_campaign(self, campaign_id: str, user_id: str):
        self.running = True
        self.user_id = user_id
        campaign = self.repo.get_campaign(campaign_id, user_id)
        if not campaign:
            self.logger.error("Campaign not found")
            return

        self.logger.info(f"Starting campaign: {campaign.name}")

        self.load_bot_instructions()
        ref_images = self.load_reference_images()

        # 1. Authenticate
        account = self.repo.get_account(campaign.account_id, user_id)
        if not account:
            self.logger.error("Account not found")
            return

        auth_result = await self.adapter.authenticate(account.session_data, account.username, account.password)
        if not auth_result:
            self.logger.error("Authentication failed. Aborting.")
            return

        self.logger.info("Authentication successful. Starting main loop.")
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
            pending = self.repo.get_pending_targets(campaign_id, self.user_id, limit=1)

            if not pending:
                self.logger.info("No pending targets. Fetching new ones...")
                await self._fetch_new_targets(campaign)
                pending = self.repo.get_pending_targets(campaign_id, self.user_id, limit=1)
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
        
        self.logger.info(f"_fetch_new_targets: targeting={targeting}, ai_instructions={campaign.ai_instructions!r}")
        
        ref_images = self.load_reference_images()
        
        # 1. Check if we need AI Strategic Planning
        if not targeting.get("sources") and self.planner and campaign.ai_instructions:
            self.logger.info("No sources defined. Triggering AI Strategic Planning...")
            plan = await self.planner.generate_discovery_plan(
                campaign.ai_instructions,
                self.adapter.platform_name,
                bot_instructions=self.bot_instructions,
                ref_images=ref_images
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
        else:
            self.logger.info(f"No AI planning needed: sources={sources}, has_planner={self.planner is not None}, has_instructions={bool(campaign.ai_instructions)}")

        strategy = targeting.get("strategy", "search")
        sources = targeting.get("sources", [])
        
        if not sources and "tags" in targeting:
            sources = targeting.get("tags", [])

        self.logger.info(f"Executing discovery strategy: {strategy} across {len(sources)} sources")

        users = []
        post_url_for_source = {}
        context = campaign.ai_instructions or ""
        for source in sources:
            if not self.running: break
            
            self.logger.info(f"Combing source: {source}")
            
            try:
                if strategy == "search":
                    new_users = await self.adapter.search_users(source, limit=10, context=context)
                elif strategy == "group_combing":
                    new_users = await self.adapter.get_group_members(source, limit=20)
                elif strategy == "post_auditing":
                    new_users = await self.adapter.get_post_commenters(source, limit=20)
                    post_url_for_source[source] = source
                elif strategy == "follower_mining":
                    new_users = await self.adapter.get_followers(source, limit=20)
                else:
                    self.logger.warning(f"Unknown discovery strategy: {strategy}")
                    new_users = []
                
                users.extend(new_users)
            except Exception as e:
                self.logger.error(f"Failed to comb {source}: {e}")

        for u in users:
            source_post = post_url_for_source.get(u.platform_id, None)
            t = Target(
                id=f"{campaign.id}_{u.platform_id}",
                user_id=self.user_id,
                campaign_id=campaign.id,
                platform_user_id=u.platform_id,
                username=u.username,
                status="pending",
                source_post_url=source_post
            )
            self.repo.add_target(t)

    async def _process_target(self, target: Target, campaign: Campaign):
        self.logger.info(f"Processing target: {target.username}")

        # 0. Capture Vision (Optional but recommended for 'eyes')
        image_base64 = await self.adapter.capture_screenshot()

        # 1. Analyze (AI)
        if self.classifier:
            profile_data = {"username": target.username, "bio": "Fetched bio..."}
            analysis = await self.classifier.classify(profile_data, image_base64=image_base64, bot_instructions=self.bot_instructions, ref_images=ref_images)
            score = analysis.get("match_score", 0.0)
            should_skip = analysis.get("should_skip", False)
            skip_reason = analysis.get("skip_reason", "")

            if should_skip:
                self.logger.info(f"Skipping {target.username}: {skip_reason}")
                self.repo.update_target_status(target.id, f"skipped_{skip_reason[:20]}" if skip_reason else "skipped_rules", ai_score=score)
                return

            if score < 0.5:
                self.repo.update_target_status(target.id, "skipped_low_score", ai_score=score)
                return

            self.repo.update_target_status(target.id, "analyzed", ai_score=score)

        # 2. Action (Follow/DM/Comment/Reply)
        action_type = campaign.campaign_type # e.g. "outreach", "growth", "engagement", "comment"

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
                    image_base64=image_base64,
                    bot_instructions=self.bot_instructions,
                    ref_images=ref_images
                )
            res = await self.adapter.send_dm(target.platform_user_id, msg)
            success = res.success
            error = res.error
        elif action_type == "comment":
            # Comment on a user's recent post
            comment_text = "Great post!"
            if self.generator:
                # Generate contextual comment based on user's profile/posts
                comment_text = await self.generator.generate_comment(
                    {"username": target.username, "bio": "Fetched bio..."},
                    campaign.message_template,
                    campaign.ai_instructions,
                    image_base64=image_base64,
                    bot_instructions=self.bot_instructions,
                    ref_images=ref_images
                )
            # Get user's recent posts first (this would need to be implemented in adapter)
            # For now, we'll skip if we can't get posts
            res = await self.adapter.comment_on_recent_post(target.platform_user_id, comment_text)
            success = res.success
            error = res.error
        elif action_type == "reply_comment":
            comment_id = getattr(target, 'comment_id', None) or target.platform_user_id
            post_url = getattr(target, 'source_post_url', None) or getattr(target, 'post_url', None)
            if not comment_id:
                self.logger.warning("No comment_id specified for reply_comment action")
                success = False
                error = "No comment_id specified"
            else:
                reply_text = "Thanks!"
                if self.generator:
                    reply_text = await self.generator.generate_reply(
                        {"username": target.username},
                        campaign.message_template,
                        campaign.ai_instructions,
                        image_base64=image_base64,
                        bot_instructions=self.bot_instructions,
                        ref_images=ref_images
                    )
                res = await self.adapter.reply_to_comment(comment_id, reply_text, post_url=post_url)
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
        
        # 4. Update memory systems for conversation and relationship tracking
        if success and action_type in ["outreach", "comment", "reply_comment"]:
            # Store conversation memory
            message_sent = ""
            if action_type == "outreach":
                message_sent = msg if 'msg' in locals() else "Hello!"
            elif action_type == "comment":
                message_sent = comment_text if 'comment_text' in locals() else "Great post!"
            elif action_type == "reply_comment":
                message_sent = reply_text if 'reply_text' in locals() else "Thanks!"
            
            await self.conversation_memory.store_conversation(
                user_id=campaign.user_id,
                platform=self.adapter.platform_name,
                target_user=target.username,
                message=message_sent,
                response="Sent successfully" if success else "Failed",
                metadata={
                    "action_type": action_type,
                    "campaign_id": campaign.id,
                    "target_id": target.id
                }
            )
            
            # Track relationship interaction
            interaction_type_map = {
                "outreach": "dm",
                "comment": "comment",
                "reply_comment": "reply"
            }
            interaction_type = interaction_type_map.get(action_type, action_type)
            
            await self.relationship_tracker.track_interaction(
                user_id=campaign.user_id,
                platform=self.adapter.platform_name,
                target_user=target.username,
                interaction_type=interaction_type,
                metadata={
                    "action_type": action_type,
                    "campaign_id": campaign.id,
                    "target_id": target.id,
                    "success": success
                }
            )

        self.repo.update_target_status(target.id, "completed" if success else "failed")
        self.anti_detect.record_action()

    def stop(self):
        self.running = False
