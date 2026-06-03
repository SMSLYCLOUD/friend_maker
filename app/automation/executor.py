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
        self._busy = False

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
            if hasattr(self.adapter, 'cleanup'):
                await self.adapter.cleanup()
            return

        self.logger.info("Authentication successful. Starting fetch→DM→next loop.")
        actions_today = 0
        limit = campaign.daily_limit or 50

        # Start background response monitor
        response_monitor_task = asyncio.create_task(self._monitor_responses(campaign))

        # Get or generate plan
        plan = await self._get_plan(campaign, ref_images)
        sources = plan.get("sources", [])
        strategy = plan.get("strategy", "follower_mining")
        fetch_limit = plan.get("fetch_limit", 20)

        if not sources:
            self.logger.error("No sources found from plan. Stopping.")
            self.running = False

        action_type = campaign.campaign_type
        context = campaign.ai_instructions or ""

        while self.running and sources:
            if actions_today >= limit:
                self.logger.info(f"Daily limit of {limit} reached.")
                break

            if self.anti_detect.needs_break():
                await self.anti_detect.take_break(lambda: self.running)
            if not self.running: break

            # Pick next source
            source = sources[0]
            self.logger.info(f"Fetching 1 target from source: {source}")

            # Fetch 1 follower from this source
            try:
                self._busy = True
                new_users = []
                if strategy == "follower_mining":
                    new_users = await self.adapter.get_followers(source, limit=1)
                elif strategy == "search":
                    new_users = await self.adapter.search_users(source, limit=1, context=context)
                elif strategy == "group_combing":
                    new_users = await self.adapter.get_group_members(source, limit=1)

                if not new_users:
                    self.logger.info(f"No more users from {source}. Moving to next source.")
                    sources.pop(0)
                    continue

                user = new_users[0]
                handle = user.platform_id.lstrip("@")

                # Skip if already contacted
                if self.repo.has_been_contacted(self.user_id, self.adapter.platform_name, handle, action_type):
                    self.logger.info(f"Skipping @{handle}: already contacted ({action_type})")
                    continue

                # Immediately DM/follow/comment this user
                self.logger.info(f"Processing @{handle} ({action_type})...")
                success = False
                error = None

                if action_type == "growth":
                    # Classify before following
                    if self.classifier:
                        profile_data = {"username": handle, "bio": ""}
                        try:
                            profile_data = await self.adapter.get_user_profile(handle)
                        except: pass
                        analysis = await self.classifier.classify(
                            profile_data, bot_instructions=self.bot_instructions,
                            ref_images=ref_images, campaign_instructions=campaign.ai_instructions or ""
                        )
                        if analysis.get("should_skip"):
                            self.logger.info(f"Skipping @{handle}: {analysis.get('skip_reason')}")
                            continue
                        if analysis.get("match_score", 0) < 0.5:
                            self.logger.info(f"Skipping @{handle}: low score ({analysis.get('match_score')})")
                            continue

                    res = await self.adapter.follow(handle)
                    success = res.success
                    error = res.error
                elif action_type == "outreach":
                    # Scrape profile for personalization
                    profile_data = {"username": handle, "bio": ""}
                    try:
                        profile_data = await self.adapter.get_user_profile(handle)
                    except Exception as e:
                        self.logger.warning(f"Failed to scrape profile: {e}")

                    # Classify before DMing
                    if self.classifier:
                        analysis = await self.classifier.classify(
                            profile_data, bot_instructions=self.bot_instructions,
                            ref_images=ref_images, campaign_instructions=campaign.ai_instructions or ""
                        )
                        if analysis.get("should_skip"):
                            self.logger.info(f"Skipping @{handle}: {analysis.get('skip_reason')}")
                            continue
                        if analysis.get("match_score", 0) < 0.5:
                            self.logger.info(f"Skipping @{handle}: low score ({analysis.get('match_score')})")
                            continue

                    # Generate and send DM
                    msg = "Hello!"
                    if self.generator:
                        msg = await self.generator.generate_dm(
                            profile_data,
                            campaign.message_template,
                            campaign.ai_instructions,
                            bot_instructions=self.bot_instructions,
                            ref_images=ref_images
                        )
                    res = await self.adapter.send_dm(handle, msg)
                    success = res.success
                    error = res.error
                    self.logger.info(f"DM to @{handle}: {'sent' if success else f'failed: {error}'}")

                elif action_type == "comment":
                    profile_data = {"username": handle, "bio": ""}
                    try:
                        profile_data = await self.adapter.get_user_profile(handle)
                    except Exception as e:
                        self.logger.warning(f"Failed to scrape profile: {e}")

                    # Classify before commenting
                    if self.classifier:
                        analysis = await self.classifier.classify(
                            profile_data, bot_instructions=self.bot_instructions,
                            ref_images=ref_images, campaign_instructions=campaign.ai_instructions or ""
                        )
                        if analysis.get("should_skip"):
                            self.logger.info(f"Skipping @{handle}: {analysis.get('skip_reason')}")
                            continue
                        if analysis.get("match_score", 0) < 0.5:
                            self.logger.info(f"Skipping @{handle}: low score ({analysis.get('match_score')})")
                            continue

                    comment_text = "Great post!"
                    if self.generator:
                        comment_text = await self.generator.generate_comment(
                            profile_data,
                            campaign.message_template,
                            campaign.ai_instructions,
                            bot_instructions=self.bot_instructions,
                            ref_images=ref_images
                        )
                    res = await self.adapter.comment_on_recent_post(handle, comment_text)
                    success = res.success
                    error = res.error

                # Log and register
                self.repo.log_action(ActionLog(
                    id=f"log_{campaign.id}_{handle}_{int(asyncio.get_event_loop().time())}",
                    account_id=campaign.account_id,
                    campaign_id=campaign.id,
                    action_type=action_type,
                    target_user=handle,
                    success=success,
                    error=error
                ))

                if success:
                    self.repo.register_contact(
                        user_id=self.user_id,
                        platform=self.adapter.platform_name,
                        platform_user_id=handle,
                        username=handle,
                        action_type=action_type,
                        campaign_id=campaign.id
                    )
                    await self.conversation_memory.store_conversation(
                        user_id=self.user_id,
                        platform=self.adapter.platform_name,
                        target_user=handle,
                        message=f"Sent {action_type} to @{handle}",
                        response="Success",
                        metadata={"action_type": action_type, "campaign_id": campaign.id}
                    )
                    actions_today += 1
                    self.logger.info(f"✓ @{handle} ({action_type}) - {actions_today}/{limit} today")
                else:
                    self.logger.warning(f"✗ @{handle} ({action_type}) failed: {error}")

                await self.anti_detect.random_delay(lambda: self.running)

            except asyncio.CancelledError:
                self.logger.info("Task cancelled.")
                raise
            except Exception as e:
                self.logger.error(f"Error processing source {source}: {e}")
                await self.anti_detect.trigger_cooldown(lambda: self.running)
            finally:
                self._busy = False

        self.logger.info("Campaign execution finished.")

        # Cancel response monitor
        if 'response_monitor_task' in dir() and not response_monitor_task.done():
            response_monitor_task.cancel()
            try:
                await response_monitor_task
            except asyncio.CancelledError:
                pass

        if not self.running:
            self.logger.info("Campaign stopped by user. Closing browser session.")
            if hasattr(self.adapter, 'cleanup'):
                await self.adapter.cleanup()
        else:
            self.logger.info("Campaign ended but browser session kept alive for next run.")

    async def _get_plan(self, campaign: Campaign, ref_images: list) -> dict:
        """Run planner and return sources, strategy, limit."""
        PLATFORM_NAMES = {"tiktok", "instagram", "twitter", "x", "facebook", "linkedin", "youtube", "reddit"}

        if self.planner and campaign.ai_instructions:
            self.logger.info("Running AI Strategic Planning...")
            plan = await self.planner.generate_discovery_plan(
                campaign.ai_instructions,
                self.adapter.platform_name,
                bot_instructions=self.bot_instructions,
                ref_images=ref_images
            )

            target_accounts = plan.get("target_accounts", [])
            keywords = plan.get("keywords", [])
            group_types = plan.get("group_types", [])
            fetch_limit = plan.get("limit", 20)

            if target_accounts:
                strategy = "follower_mining"
                sources = [s.lstrip("@") for s in target_accounts if s.lower().strip("@") not in PLATFORM_NAMES]
            elif group_types:
                strategy = "group_combing"
                sources = [s.lstrip("@") for s in group_types if s.lower().strip("@") not in PLATFORM_NAMES]
            else:
                strategy = "search"
                sources = [s for s in keywords if s.lower() not in PLATFORM_NAMES]

            self.logger.info(f"Plan: {len(sources)} sources ({sources}), strategy={strategy}, limit={fetch_limit}")
            return {"sources": sources, "strategy": strategy, "fetch_limit": fetch_limit}

        self.logger.info("No planner available. Using campaign targeting.")
        targeting = campaign.targeting
        sources = [s.lstrip("@") for s in targeting.get("sources", []) if s.lstrip("@").lower() not in PLATFORM_NAMES]
        strategy = targeting.get("strategy", "search")
        fetch_limit = targeting.get("fetch_limit", 20)
        return {"sources": sources, "strategy": strategy, "fetch_limit": fetch_limit}

    async def _fetch_new_targets(self, campaign: Campaign):
        """Search for or discover users based on campaign targeting settings."""
        targeting = campaign.targeting
        
        self.logger.info(f"_fetch_new_targets: targeting={targeting}, ai_instructions={campaign.ai_instructions!r}")
        
        ref_images = self.load_reference_images()
        
        PLATFORM_NAMES = {"tiktok", "instagram", "twitter", "x", "facebook", "linkedin", "youtube", "reddit"}
        mined_sources = set(targeting.get("mined_sources", []))
        existing_sources = targeting.get("sources", [])
        
        # Clean stale sources: strip @, filter platform names and empty strings
        clean_sources = []
        for s in existing_sources:
            s_clean = s.lstrip("@").strip().lower()
            if s_clean and s_clean not in PLATFORM_NAMES:
                clean_sources.append(s.lstrip("@"))
        
        # Always re-plan if instruction is set and planner is available
        # This ensures the strict planner prompt is applied every time
        if self.planner and campaign.ai_instructions:
            self.logger.info("Re-running AI Strategic Planning with current instruction...")
            plan = await self.planner.generate_discovery_plan(
                campaign.ai_instructions,
                self.adapter.platform_name,
                bot_instructions=self.bot_instructions,
                ref_images=ref_images
            )
            
            target_accounts = plan.get("target_accounts", [])
            keywords = plan.get("keywords", [])
            group_types = plan.get("group_types", [])
            fetch_limit = plan.get("limit", 20)
            
            if target_accounts:
                strategy = "follower_mining"
                sources = [s.lstrip("@") for s in target_accounts if s.lower().strip("@") not in PLATFORM_NAMES]
            elif group_types:
                strategy = "group_combing"
                sources = [s.lstrip("@") for s in group_types if s.lower().strip("@") not in PLATFORM_NAMES]
            else:
                strategy = "search"
                sources = [s for s in keywords if s.lower() not in PLATFORM_NAMES]
            
            # Update targeting with fresh plan
            targeting["sources"] = sources
            targeting["strategy"] = strategy
            targeting["fetch_limit"] = fetch_limit
            targeting["mined_sources"] = []
            import json
            campaign.targeting_json = json.dumps(targeting)
            self.repo.update_campaign(campaign)
            
            self.logger.info(f"AI Plan: {len(sources)} sources, strategy={strategy}, limit={fetch_limit}")
        else:
            self.logger.info(f"No planner available: has_planner={self.planner is not None}, has_instructions={bool(campaign.ai_instructions)}")

        strategy = targeting.get("strategy", "search")
        sources = targeting.get("sources", [])
        fetch_limit = targeting.get("fetch_limit", 20)
        
        if not sources and "tags" in targeting:
            sources = targeting.get("tags", [])

        # Strip any leftover @ from sources
        sources = [s.lstrip("@") for s in sources]

        # Skip sources that have already been mined
        sources = [s for s in sources if s not in mined_sources]
        
        if not sources:
            self.logger.info("All sources have been mined already. Campaign discovery complete.")
            return

        self.logger.info(f"Executing discovery strategy: {strategy} across {len(sources)} sources, limit={fetch_limit} (skipped {len(mined_sources)} already mined)")

        users = []
        post_url_for_source = {}
        context = campaign.ai_instructions or ""
        for source in sources:
            if not self.running: break
            
            self.logger.info(f"Combing source: {source}")
            
            try:
                if strategy == "search":
                    new_users = await self.adapter.search_users(source, limit=fetch_limit, context=context)
                elif strategy == "group_combing":
                    new_users = await self.adapter.get_group_members(source, limit=fetch_limit)
                elif strategy == "post_auditing":
                    new_users = await self.adapter.get_post_commenters(source, limit=fetch_limit)
                    post_url_for_source[source] = source
                elif strategy == "follower_mining":
                    new_users = await self.adapter.get_followers(source, limit=fetch_limit)
                else:
                    self.logger.warning(f"Unknown discovery strategy: {strategy}")
                    new_users = []
                
                users.extend(new_users)
            except Exception as e:
                self.logger.error(f"Failed to comb {source}: {e}")
            
            # Mark source as mined
            mined_sources.add(source)
            targeting["mined_sources"] = list(mined_sources)
            import json
            campaign.targeting_json = json.dumps(targeting)
            self.repo.update_campaign(campaign)

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
        handle = target.platform_user_id.lstrip("@")

        # 0. Scrape user's profile for bio, posts
        profile_data = {"username": target.username, "bio": ""}
        try:
            profile_data = await self.adapter.get_user_profile(handle)
            self.logger.info(f"Scraped profile for {target.username}: bio={profile_data.get('bio', '')[:80]}")
        except Exception as e:
            self.logger.warning(f"Failed to scrape profile for {target.username}: {e}")

        image_base64 = None

        # 1. Analyze (AI)
        if self.classifier:
            analysis = await self.classifier.classify(
                profile_data,
                image_base64=image_base64,
                bot_instructions=self.bot_instructions,
                ref_images=ref_images,
                campaign_instructions=campaign.ai_instructions or ""
            )
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
        action_type = campaign.campaign_type

        success = False
        error = None

        if action_type == "growth":
            res = await self.adapter.follow(handle)
            success = res.success
            error = res.error
        elif action_type == "outreach":
            msg = "Hello!"
            if self.generator:
                msg = await self.generator.generate_dm(
                    profile_data,
                    campaign.message_template,
                    campaign.ai_instructions,
                    image_base64=image_base64,
                    bot_instructions=self.bot_instructions,
                    ref_images=ref_images
                )
            res = await self.adapter.send_dm(handle, msg)
            success = res.success
            error = res.error
        elif action_type == "comment":
            comment_text = "Great post!"
            if self.generator:
                comment_text = await self.generator.generate_comment(
                    profile_data,
                    campaign.message_template,
                    campaign.ai_instructions,
                    image_base64=image_base64,
                    bot_instructions=self.bot_instructions,
                    ref_images=ref_images
                )
            res = await self.adapter.comment_on_recent_post(handle, comment_text)
            success = res.success
            error = res.error
        elif action_type == "reply_comment":
            comment_id = getattr(target, 'comment_id', None) or handle
            post_url = getattr(target, 'source_post_url', None) or getattr(target, 'post_url', None)
            if not comment_id:
                self.logger.warning("No comment_id specified for reply_comment action")
                success = False
                error = "No comment_id specified"
            else:
                reply_text = "Thanks!"
                if self.generator:
                    reply_text = await self.generator.generate_reply(
                        profile_data,
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

        # Register in cross-campaign dedup registry
        if success:
            handle = target.platform_user_id.lstrip("@")
            self.repo.register_contact(
                user_id=self.user_id,
                platform=self.adapter.platform_name,
                platform_user_id=handle,
                username=target.username,
                action_type=action_type,
                campaign_id=campaign.id
            )
            self.logger.info(f"Registered @{handle} in contact registry ({action_type})")

    async def _monitor_responses(self, campaign: Campaign):
        """Background task: check inbox for responses and send follow-ups."""
        self.logger.info("Response monitor started. Checking inbox every 120s.")
        check_interval = 120

        while self.running:
            await asyncio.sleep(check_interval)
            if not self.running:
                break

            # Skip if main loop is busy (don't compete for browser session)
            if self._busy:
                self.logger.info("Response monitor: main loop busy, skipping inbox check.")
                continue

            try:
                self.logger.info("Checking inbox for responses...")
                unread = await self.adapter.check_inbox(limit=5)

                if not unread:
                    self.logger.info("No unread messages found.")
                    continue

                for convo in unread:
                    if not self.running:
                        break

                    username = convo.get("username", "")
                    their_message = convo.get("latest_message", "")
                    if not username or not their_message:
                        continue

                    self.logger.info(f"Response from @{username}: {their_message[:80]}...")

                    # Read full conversation history
                    history_messages = await self.adapter.read_conversation(username, limit=10)
                    conversation_history = "\n".join(
                        f"{'Me' if m.get('sender') == 'me' else m.get('sender', username)}: {m.get('content', '')}"
                        for m in history_messages
                    )

                    # Get stored context from our side
                    stored_context = await self.conversation_memory.get_context_for_target(
                        user_id=self.user_id,
                        platform=self.adapter.platform_name,
                        target_user=username
                    )

                    # Scrape their profile for personalization
                    profile_data = {"username": username, "bio": ""}
                    try:
                        profile_data = await self.adapter.get_user_profile(username)
                    except Exception as e:
                        self.logger.warning(f"Failed to scrape profile for @{username}: {e}")

                    # Generate reply
                    reply_text = ""
                    if self.generator:
                        full_history = ""
                        if stored_context:
                            full_history += stored_context + "\n"
                        if conversation_history:
                            full_history += conversation_history

                        reply_text = await self.generator.generate_reply(
                            profile_data,
                            campaign.message_template,
                            campaign.ai_instructions,
                            bot_instructions=self.bot_instructions,
                            conversation_history=full_history,
                            their_message=their_message
                        )
                    else:
                        reply_text = f"Thanks for your message! I'll get back to you soon."

                    if not reply_text:
                        continue

                    # Send reply
                    self.logger.info(f"Sending follow-up to @{username}: {reply_text[:80]}...")
                    res = await self.adapter.send_dm(username, reply_text)

                    if res.success:
                        # Store conversation memory
                        await self.conversation_memory.store_conversation(
                            user_id=self.user_id,
                            platform=self.adapter.platform_name,
                            target_user=username,
                            message=reply_text,
                            response=f"Replied to: {their_message[:100]}",
                            metadata={"action_type": "follow_up", "campaign_id": campaign.id}
                        )
                        await self.relationship_tracker.track_interaction(
                            user_id=self.user_id,
                            platform=self.adapter.platform_name,
                            target_user=username,
                            interaction_type="follow_up",
                            metadata={"campaign_id": campaign.id, "their_message": their_message[:200]}
                        )
                        # Register follow-up in dedup registry
                        self.repo.register_contact(
                            user_id=self.user_id,
                            platform=self.adapter.platform_name,
                            platform_user_id=username,
                            username=username,
                            action_type="follow_up",
                            campaign_id=campaign.id
                        )
                        self.logger.info(f"Follow-up sent to @{username} successfully.")
                    else:
                        self.logger.error(f"Failed to send follow-up to @{username}: {res.error}")

            except Exception as e:
                self.logger.error(f"Response monitor error: {e}")

        self.logger.info("Response monitor stopped.")

    def stop(self):
        self.running = False
