from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import json

class Account(BaseModel):
    id: str
    platform: str
    username: str
    display_name: Optional[str] = None
    session_data: Optional[str] = None  # Encrypted string
    proxy_config: Optional[str] = None
    is_active: bool = True
    last_action_at: Optional[int] = None
    daily_actions: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

class Campaign(BaseModel):
    id: str
    account_id: str
    name: str
    campaign_type: str
    status: str = "draft"
    targeting_json: Optional[str] = None
    message_template: Optional[str] = None
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
    campaign_id: str
    platform_user_id: str
    username: Optional[str] = None
    profile_json: Optional[str] = None
    ai_score: Optional[float] = None
    status: str = "pending"
    processed_at: Optional[int] = None

class ActionLog(BaseModel):
    id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    action_type: str
    target_user: Optional[str] = None
    success: bool
    error: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
