import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database.repository import Repository
from app.database.models import ConversationMemory, RelationshipTracker, ScheduledAction

logger = logging.getLogger("ConversationMemory")

class ConversationMemoryManager:
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def store_conversation(self, user_id: str, platform: str, target_user: str, 
                                message: str, response: str, metadata: Dict[str, Any] = None):
        """Store a conversation exchange for context maintenance"""
        try:
            memory = ConversationMemory(
                id=f"conv_{user_id}_{platform}_{target_user}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                platform=platform,
                target_user=target_user,
                message=message,
                response=response,
                timestamp=int(datetime.now().timestamp()),
                metadata=json.dumps(metadata or {})
            )
            self.repo.store_conversation_memory(memory)
            logger.debug(f"Stored conversation: {user_id} -> {target_user} on {platform}")
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
    
    async def get_conversation_history(self, user_id: str, platform: str, target_user: str, 
                                     limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve conversation history for context"""
        try:
            memories = self.repo.get_conversation_memory(user_id, platform, target_user, limit)
            return [
                {
                    "message": m.message,
                    "response": m.response,
                    "timestamp": m.timestamp,
                    "metadata": json.loads(m.metadata) if m.metadata else {}
                }
                for m in memories
            ]
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def get_context_for_target(self, user_id: str, platform: str, target_user: str, 
                                   max_chars: int = 1000) -> str:
        """Get formatted conversation context for AI processing"""
        try:
            history = await self.get_conversation_history(user_id, platform, target_user, limit=5)
            if not history:
                return ""
            
            context_parts = []
            for entry in reversed(history):  # Most recent first
                timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
                context_parts.append(f"[{timestamp}] You: {entry['message']}")
                context_parts.append(f"[{timestamp}] Them: {entry['response']}")
            
            context = "\n".join(context_parts)
            # Truncate if too long
            if len(context) > max_chars:
                context = context[-max_chars:]
                # Try to start at a boundary
                if "\n" in context[:50]:
                    context = context[context.find("\n")+1:]
            
            return f"Previous conversation context:\n{context}"
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return ""

class RelationshipTrackerManager:
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def track_interaction(self, user_id: str, platform: str, target_user: str, 
                              interaction_type: str, metadata: Dict[str, Any] = None):
        """Track an interaction for relationship building"""
        try:
            # Update or create relationship tracker
            tracker = self.repo.get_relationship_tracker(user_id, platform, target_user)
            if tracker:
                tracker.interaction_count += 1
                tracker.last_interaction = int(datetime.now().timestamp())
                tracker.last_interaction_type = interaction_type
                if metadata:
                    tracker.metadata = json.dumps({**json.loads(tracker.metadata or "{}"), **metadata})
            else:
                tracker = RelationshipTracker(
                    id=f"rel_{user_id}_{platform}_{target_user}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    platform=platform,
                    target_user=target_user,
                    interaction_count=1,
                    last_interaction=int(datetime.now().timestamp()),
                    last_interaction_type=interaction_type,
                    metadata=json.dumps(metadata or {})
                )
            self.repo.save_relationship_tracker(tracker)
            logger.debug(f"Tracked {interaction_type} interaction: {user_id} -> {target_user} on {platform}")
        except Exception as e:
            logger.error(f"Failed to track interaction: {e}")
    
    async def get_relationship_score(self, user_id: str, platform: str, target_user: str) -> float:
        """Get a relationship score (0-1) based on interaction history"""
        try:
            tracker = self.repo.get_relationship_tracker(user_id, platform, target_user)
            if not tracker:
                return 0.0
            
            # Simple scoring based on interaction count and recency
            interaction_score = min(tracker.interaction_count / 10.0, 1.0)  # Max at 10 interactions
            
            # Recency factor (more recent = higher score)
            now = int(datetime.now().timestamp())
            days_since = (now - tracker.last_interaction) / (24 * 3600)
            recency_score = max(0.0, 1.0 - (days_since / 30.0))  # Decay over 30 days
            
            return (interaction_score * 0.7) + (recency_score * 0.3)
        except Exception as e:
            logger.error(f"Failed to get relationship score: {e}")
            return 0.0
    
    async def get_relationship_summary(self, user_id: str, platform: str, target_user: str) -> Dict[str, Any]:
        """Get detailed relationship information"""
        try:
            tracker = self.repo.get_relationship_tracker(user_id, platform, target_user)
            if not tracker:
                return {
                    "interaction_count": 0,
                    "last_interaction": None,
                    "relationship_score": 0.0
                }
            
            return {
                "interaction_count": tracker.interaction_count,
                "last_interaction": tracker.last_interaction,
                "last_interaction_type": tracker.last_interaction_type,
                "relationship_score": await self.get_relationship_score(user_id, platform, target_user),
                "metadata": json.loads(tracker.metadata or "{}")
            }
        except Exception as e:
            logger.error(f"Failed to get relationship summary: {e}")
            return {
                "interaction_count": 0,
                "last_interaction": None,
                "relationship_score": 0.0
            }

class ScheduledActionManager:
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def create_scheduled_action(self, user_id: str, platform: str, action_type: str,
                                    target_user: str = None, parameters: Dict[str, Any] = None,
                                    cron_expression: str = None, start_time: int = None,
                                    end_time: int = None) -> str:
        """Create a scheduled recurring action"""
        try:
            action_id = f"sched_{user_id}_{platform}_{action_type}_{int(datetime.now().timestamp())}"
            scheduled_action = ScheduledAction(
                id=action_id,
                user_id=user_id,
                platform=platform,
                action_type=action_type,
                target_user=target_user,
                parameters=json.dumps(parameters or {}),
                cron_expression=cron_expression,
                start_time=start_time or int(datetime.now().timestamp()),
                end_time=end_time,
                is_active=True,
                created_at=int(datetime.now().timestamp())
            )
            self.repo.save_scheduled_action(scheduled_action)
            logger.info(f"Created scheduled action: {action_id}")
            return action_id
        except Exception as e:
            logger.error(f"Failed to create scheduled action: {e}")
            raise
    
    async def get_due_actions(self, current_time: int = None) -> List[Dict[str, Any]]:
        """Get actions that are due to run"""
        try:
            if current_time is None:
                current_time = int(datetime.now().timestamp())
            
            actions = self.repo.get_due_scheduled_actions(current_time)
            return [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "platform": a.platform,
                    "action_type": a.action_type,
                    "target_user": a.target_user,
                    "parameters": json.loads(a.parameters) if a.parameters else {},
                    "cron_expression": a.cron_expression
                }
                for a in actions
            ]
        except Exception as e:
            logger.error(f"Failed to get due actions: {e}")
            return []
    
    async def mark_action_completed(self, action_id: str, next_run_time: int = None):
        """Mark a scheduled action as completed and update next run time"""
        try:
            self.repo.update_scheduled_action_last_run(action_id, int(datetime.now().timestamp()))
            if next_run_time:
                self.repo.update_scheduled_action_next_run(action_id, next_run_time)
            logger.debug(f"Marked scheduled action as completed: {action_id}")
        except Exception as e:
            logger.error(f"Failed to mark action completed: {e}")

# Factory functions for dependency injection
def get_conversation_memory(repository: Repository) -> ConversationMemoryManager:
    return ConversationMemoryManager(repository)

def get_relationship_tracker(repository: Repository) -> RelationshipTrackerManager:
    return RelationshipTrackerManager(repository)

def get_scheduled_action_manager(repository: Repository) -> ScheduledActionManager:
    return ScheduledActionManager(repository)