from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import json

class Account(BaseModel):
    id: str
    user_id: str
    platform: str
    username: str
    password: Optional[str] = None
    display_name: Optional[str] = None
    session_data: Optional[str] = None
    proxy_config: Optional[str] = None
    is_active: bool = True
    last_action_at: Optional[int] = None
    daily_actions: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

class Campaign(BaseModel):
    id: str
    user_id: str
    account_id: str
    name: str
    campaign_type: str
    status: str = "draft"
    targeting_json: Optional[str] = None
    message_template: Optional[str] = None
    ai_instructions: Optional[str] = None
    schedule_json: Optional[str] = None
    daily_limit: int = 50
    total_actions: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    @property
    def targeting(self) -> Dict[str, Any]:
        return json.loads(self.targeting_json) if self.targeting_json else {}

    @property
    def schedule(self) -> Dict[str, Any]:
        return json.loads(self.schedule_json) if self.schedule_json else {}

class Target(BaseModel):
    id: str
    user_id: str
    campaign_id: str
    platform_user_id: str
    username: Optional[str] = None
    profile_json: Optional[str] = None
    ai_score: Optional[float] = None
    status: str = "pending"
    processed_at: Optional[int] = None
    comment_id: Optional[str] = None
    post_url: Optional[str] = None
    source_post_url: Optional[str] = None

class ActionLog(BaseModel):
    id: str
    user_id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    action_type: str
    target_user: Optional[str] = None
    success: bool
    error: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

# New models for long-term interaction capabilities
class ConversationMemory(BaseModel):
    id: str
    user_id: str
    platform: str
    target_user: str
    message: str
    response: str
    timestamp: int
    metadata: Optional[str] = None

class RelationshipTracker(BaseModel):
    id: str
    user_id: str
    platform: str
    target_user: str
    interaction_count: int = 0
    last_interaction: Optional[int] = None
    last_interaction_type: Optional[str] = None
    metadata: Optional[str] = None

class ScheduledAction(BaseModel):
    id: str
    user_id: str
    platform: str
    action_type: str
    target_user: Optional[str] = None
    parameters: Optional[str] = None
    cron_expression: Optional[str] = None
    start_time: int
    end_time: Optional[int] = None
    is_active: bool = True
    created_at: int
    last_run_at: Optional[int] = None

class FollowBack(BaseModel):
    id: str
    user_id: str
    campaign_id: str
    platform: str
    target_username: str
    followed_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    follow_back_checked_at: Optional[int] = None
    has_followed_back: bool = False
    dm_sent: bool = False
    dm_sent_at: Optional[int] = None
    dm_message: Optional[str] = None
    status: str = "pending"  # pending, followed_back, dm_sent, expired
