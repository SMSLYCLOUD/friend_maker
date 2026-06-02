import json
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import text
from app.database.connection import SessionLocal
from app.database.models import Account, Campaign, Target, ActionLog, ConversationMemory, RelationshipTracker, ScheduledAction
from app.utils.crypto import crypto

class Repository:
    def __init__(self):
        self.session = SessionLocal()

    def _row_to_dict(self, row) -> dict:
        return row._asdict() if hasattr(row, '_asdict') else dict(row)

    # --- User Operations ---
    def create_user(self, username: str, password_hash: str) -> str:
        uid = str(uuid.uuid4())
        query = text("INSERT INTO users (id, username, hashed_password, created_at) VALUES (:id, :username, :password, :created_at)")
        self.session.execute(query, {
            "id": uid, "username": username, "password": password_hash,
            "created_at": int(time.time())
        })
        self.session.commit()
        return uid

    def get_user(self, username: str):
        query = text("SELECT * FROM users WHERE username = :username")
        result = self.session.execute(query, {"username": username})
        row = result.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_user_by_id(self, user_id: str):
        query = text("SELECT * FROM users WHERE id = :id")
        result = self.session.execute(query, {"id": user_id})
        row = result.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    # --- Account Operations ---
    def create_account(self, account: Account) -> Account:
        query = text("""
        INSERT INTO accounts (id, user_id, platform, username, password, display_name, session_data, proxy_config, is_active, created_at)
        VALUES (:id, :user_id, :platform, :username, :password, :display_name, :session_data, :proxy_config, :is_active, :created_at)
        """)
        encrypted_session = crypto.encrypt(account.session_data) if account.session_data else None
        encrypted_password = crypto.encrypt(account.password) if account.password else None
        self.session.execute(query, {
            "id": account.id, "user_id": account.user_id, "platform": account.platform,
            "username": account.username, "password": encrypted_password,
            "display_name": account.display_name, "session_data": encrypted_session,
            "proxy_config": account.proxy_config, "is_active": 1 if account.is_active else 0,
            "created_at": account.created_at
        })
        self.session.commit()
        return account

    def get_account(self, account_id: str, user_id: str) -> Optional[Account]:
        query = text("SELECT * FROM accounts WHERE id = :id AND user_id = :user_id")
        result = self.session.execute(query, {"id": account_id, "user_id": user_id})
        row = result.fetchone()
        if not row:
            return None
        data = self._row_to_dict(row)
        if data['session_data']:
            data['session_data'] = crypto.decrypt(data['session_data'])
        if 'password' in data and data['password']:
            data['password'] = crypto.decrypt(data['password'])
        data['is_active'] = bool(data['is_active'])
        return Account(**data)

    def list_accounts(self, user_id: str) -> List[Account]:
        query = text("SELECT * FROM accounts WHERE user_id = :user_id")
        result = self.session.execute(query, {"user_id": user_id})
        accounts = []
        for row in result.fetchall():
            data = self._row_to_dict(row)
            if data['session_data']:
                data['session_data'] = crypto.decrypt(data['session_data'])
            if 'password' in data and data['password']:
                data['password'] = crypto.decrypt(data['password'])
            data['is_active'] = bool(data['is_active'])
            accounts.append(Account(**data))
        return accounts

    def update_account_session(self, account_id: str, user_id: str, session_data: str):
        query = text("UPDATE accounts SET session_data = :data WHERE id = :id AND user_id = :user_id")
        encrypted = crypto.encrypt(session_data)
        self.session.execute(query, {"data": encrypted, "id": account_id, "user_id": user_id})
        self.session.commit()

    # --- Campaign Operations ---
    def create_campaign(self, campaign: Campaign) -> Campaign:
        query = text("""
        INSERT INTO campaigns (id, user_id, account_id, name, campaign_type, status, targeting_json, message_template, ai_instructions, schedule_json, daily_limit, created_at)
        VALUES (:id, :user_id, :account_id, :name, :campaign_type, :status, :targeting_json, :message_template, :ai_instructions, :schedule_json, :daily_limit, :created_at)
        """)
        self.session.execute(query, {
            "id": campaign.id, "user_id": campaign.user_id, "account_id": campaign.account_id,
            "name": campaign.name, "campaign_type": campaign.campaign_type,
            "status": campaign.status, "targeting_json": campaign.targeting_json,
            "message_template": campaign.message_template, "ai_instructions": campaign.ai_instructions,
            "schedule_json": campaign.schedule_json, "daily_limit": campaign.daily_limit,
            "created_at": campaign.created_at
        })
        self.session.commit()
        return campaign

    def get_campaign(self, campaign_id: str, user_id: str) -> Optional[Campaign]:
        query = text("SELECT * FROM campaigns WHERE id = :id AND user_id = :user_id")
        result = self.session.execute(query, {"id": campaign_id, "user_id": user_id})
        row = result.fetchone()
        if not row:
            return None
        return Campaign(**self._row_to_dict(row))

    def get_campaign_by_id(self, campaign_id: str) -> Optional[Campaign]:
        query = text("SELECT * FROM campaigns WHERE id = :id")
        result = self.session.execute(query, {"id": campaign_id})
        row = result.fetchone()
        if not row:
            return None
        return Campaign(**self._row_to_dict(row))

    def update_campaign(self, campaign: Campaign):
        query = text("""
        UPDATE campaigns
        SET status = :status, targeting_json = :targeting, message_template = :template,
            ai_instructions = :ai, schedule_json = :schedule, daily_limit = :limit,
            total_actions = :total
        WHERE id = :id AND user_id = :user_id
        """)
        self.session.execute(query, {
            "status": campaign.status, "targeting": campaign.targeting_json,
            "template": campaign.message_template, "ai": campaign.ai_instructions,
            "schedule": campaign.schedule_json, "limit": campaign.daily_limit,
            "total": campaign.total_actions, "id": campaign.id, "user_id": campaign.user_id
        })
        self.session.commit()

    def list_campaigns(self, user_id: str) -> List[Campaign]:
        query = text("SELECT * FROM campaigns WHERE user_id = :user_id ORDER BY created_at DESC")
        result = self.session.execute(query, {"user_id": user_id})
        return [Campaign(**self._row_to_dict(row)) for row in result.fetchall()]

    # --- Target Operations ---
    def add_target(self, target: Target):
        query = text("""
        INSERT INTO targets (id, user_id, campaign_id, platform_user_id, username, profile_json, status, comment_id, post_url, source_post_url)
        VALUES (:id, :user_id, :campaign_id, :platform_user_id, :username, :profile_json, :status, :comment_id, :post_url, :source_post_url)
        ON CONFLICT DO NOTHING
        """)
        self.session.execute(query, {
            "id": target.id, "user_id": target.user_id, "campaign_id": target.campaign_id,
            "platform_user_id": target.platform_user_id, "username": target.username,
            "profile_json": target.profile_json, "status": target.status,
            "comment_id": target.comment_id, "post_url": target.post_url,
            "source_post_url": target.source_post_url
        })
        self.session.commit()

    def get_pending_targets(self, campaign_id: str, user_id: str, limit: int = 10) -> List[Target]:
        query = text("SELECT * FROM targets WHERE campaign_id = :id AND user_id = :user_id AND status = 'pending' LIMIT :limit")
        result = self.session.execute(query, {"id": campaign_id, "user_id": user_id, "limit": limit})
        return [Target(**self._row_to_dict(row)) for row in result.fetchall()]

    def update_target_status(self, target_id: str, status: str, ai_score: float = None):
        if ai_score is not None:
            query = text("UPDATE targets SET status = :status, ai_score = :score WHERE id = :id")
            self.session.execute(query, {"status": status, "score": ai_score, "id": target_id})
        else:
            query = text("UPDATE targets SET status = :status WHERE id = :id")
            self.session.execute(query, {"status": status, "id": target_id})
        self.session.commit()

    # --- Action Logs ---
    def log_action(self, log: ActionLog):
        query = text("""
        INSERT INTO action_logs (id, user_id, account_id, campaign_id, action_type, target_user, success, error, created_at)
        VALUES (:id, :user_id, :account_id, :campaign_id, :action_type, :target_user, :success, :error, :created_at)
        """)
        self.session.execute(query, {
            "id": log.id, "user_id": log.user_id, "account_id": log.account_id,
            "campaign_id": log.campaign_id, "action_type": log.action_type,
            "target_user": log.target_user, "success": 1 if log.success else 0,
            "error": log.error, "created_at": log.created_at
        })
        self.session.commit()

    def get_analytics_summary(self, user_id: str):
        total_actions = self.session.execute(
            text("SELECT COUNT(*) FROM action_logs WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).scalar() or 0

        now = int(time.time())
        day_ago = now - 86400
        today_actions = self.session.execute(
            text("SELECT COUNT(*) FROM action_logs WHERE user_id = :user_id AND created_at > :start"),
            {"user_id": user_id, "start": day_ago}
        ).scalar() or 0

        res = self.session.execute(
            text("SELECT AVG(CAST(success AS FLOAT)) FROM action_logs WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).scalar() or 0.0

        success_rate = float(res) if res is not None else 0.0

        return {
            "total_actions": total_actions,
            "today_actions": today_actions,
            "success_rate": success_rate
        }

    # --- Conversation Memory Operations ---
    def store_conversation_memory(self, memory: ConversationMemory):
        query = text("""
        INSERT INTO conversation_memory (id, user_id, platform, target_user, message, response, timestamp, metadata)
        VALUES (:id, :user_id, :platform, :target_user, :message, :response, :timestamp, :metadata)
        """)
        self.session.execute(query, {
            "id": memory.id, "user_id": memory.user_id, "platform": memory.platform,
            "target_user": memory.target_user, "message": memory.message, "response": memory.response,
            "timestamp": memory.timestamp, "metadata": memory.metadata
        })
        self.session.commit()

    def get_conversation_memory(self, user_id: str, platform: str, target_user: str, limit: int = 10) -> List[ConversationMemory]:
        query = text("""
        SELECT * FROM conversation_memory 
        WHERE user_id = :user_id AND platform = :platform AND target_user = :target_user
        ORDER BY timestamp DESC LIMIT :limit
        """)
        result = self.session.execute(query, {
            "user_id": user_id, "platform": platform, "target_user": target_user, "limit": limit
        })
        return [ConversationMemory(**self._row_to_dict(row)) for row in result.fetchall()]

    # --- Relationship Tracker Operations ---
    def get_relationship_tracker(self, user_id: str, platform: str, target_user: str) -> Optional[RelationshipTracker]:
        query = text("""
        SELECT * FROM relationship_tracker 
        WHERE user_id = :user_id AND platform = :platform AND target_user = :target_user
        """)
        result = self.session.execute(query, {
            "user_id": user_id, "platform": platform, "target_user": target_user
        })
        row = result.fetchone()
        if not row:
            return None
        return RelationshipTracker(**self._row_to_dict(row))

    def save_relationship_tracker(self, tracker: RelationshipTracker):
        # Check if exists
        existing = self.get_relationship_tracker(tracker.user_id, tracker.platform, tracker.target_user)
        if existing:
            # Update
            query = text("""
            UPDATE relationship_tracker SET 
                interaction_count = :interaction_count,
                last_interaction = :last_interaction,
                last_interaction_type = :last_interaction_type,
                metadata = :metadata
            WHERE user_id = :user_id AND platform = :platform AND target_user = :target_user
            """)
            self.session.execute(query, {
                "interaction_count": tracker.interaction_count,
                "last_interaction": tracker.last_interaction,
                "last_interaction_type": tracker.last_interaction_type,
                "metadata": tracker.metadata,
                "user_id": tracker.user_id,
                "platform": tracker.platform,
                "target_user": tracker.target_user
            })
        else:
            # Insert
            query = text("""
            INSERT INTO relationship_tracker (id, user_id, platform, target_user, interaction_count, 
                                            last_interaction, last_interaction_type, metadata)
            VALUES (:id, :user_id, :platform, :target_user, :interaction_count, 
                    :last_interaction, :last_interaction_type, :metadata)
            """)
            self.session.execute(query, {
                "id": tracker.id, "user_id": tracker.user_id, "platform": tracker.platform,
                "target_user": tracker.target_user, "interaction_count": tracker.interaction_count,
                "last_interaction": tracker.last_interaction,
                "last_interaction_type": tracker.last_interaction_type,
                "metadata": tracker.metadata
            })
        self.session.commit()

    # --- Scheduled Action Operations ---
    def save_scheduled_action(self, action: ScheduledAction):
        query = text("""
        INSERT INTO scheduled_actions (id, user_id, platform, action_type, target_user, parameters, 
                                     cron_expression, start_time, end_time, is_active, created_at, last_run_at)
        VALUES (:id, :user_id, :platform, :action_type, :target_user, :parameters, 
                :cron_expression, :start_time, :end_time, :is_active, :created_at, :last_run_at)
        """)
        self.session.execute(query, {
            "id": action.id, "user_id": action.user_id, "platform": action.platform,
            "action_type": action.action_type, "target_user": action.target_user,
            "parameters": action.parameters, "cron_expression": action.cron_expression,
            "start_time": action.start_time, "end_time": action.end_time,
            "is_active": action.is_active, "created_at": action.created_at,
            "last_run_at": action.last_run_at
        })
        self.session.commit()

    def update_scheduled_action_last_run(self, action_id: str, last_run_at: int):
        query = text("""
        UPDATE scheduled_actions SET last_run_at = :last_run_at WHERE id = :id
        """)
        self.session.execute(query, {"last_run_at": last_run_at, "id": action_id})
        self.session.commit()

    def update_scheduled_action_next_run(self, action_id: str, next_run_time: int):
        # For simplicity, we'll store next run time in a custom field or calculate from cron
        # In a full implementation, this would update a next_run_time column
        pass  # Placeholder - would need DB schema update for next_run_time column

    def get_due_scheduled_actions(self, current_time: int) -> List[ScheduledAction]:
        query = text("""
        SELECT * FROM scheduled_actions 
        WHERE is_active = 1 
        AND start_time <= :current_time
        AND (end_time IS NULL OR end_time >= :current_time)
        """)
        result = self.session.execute(query, {"current_time": current_time})
        return [ScheduledAction(**self._row_to_dict(row)) for row in result.fetchall()]

    def delete_campaign(self, campaign_id: str, user_id: str):
        query = text("DELETE FROM campaigns WHERE id = :id AND user_id = :user_id")
        self.session.execute(query, {"id": campaign_id, "user_id": user_id})
        self.session.commit()

    def delete_account(self, account_id: str, user_id: str):
        query = text("DELETE FROM accounts WHERE id = :id AND user_id = :user_id")
        self.session.execute(query, {"id": account_id, "user_id": user_id})
        self.session.commit()

    def get_activity_feed(self, user_id: str, limit: int = 10):
        query = text("""
        SELECT action_logs.*, accounts.platform FROM action_logs
        LEFT JOIN accounts ON action_logs.account_id = accounts.id
        WHERE action_logs.user_id = :user_id
        ORDER BY action_logs.created_at DESC LIMIT :limit
        """)
        result = self.session.execute(query, {"user_id": user_id, "limit": limit})
        return [self._row_to_dict(row) for row in result.fetchall()]

    def get_audience_insights(self, user_id: str):
        total = self.session.execute(
            text("SELECT COUNT(*) FROM targets WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).scalar() or 0

        processed = self.session.execute(
            text("SELECT COUNT(*) FROM targets WHERE user_id = :user_id AND status != 'pending'"),
            {"user_id": user_id}
        ).scalar() or 0

        avg_score = self.session.execute(
            text("SELECT AVG(ai_score) FROM targets WHERE user_id = :user_id AND ai_score IS NOT NULL"),
            {"user_id": user_id}
        ).scalar()

        return {
            "total_targets": total,
            "processed_targets": processed,
            "avg_ai_score": round(avg_score, 2) if avg_score is not None else 0.0
        }

    def close(self):
        self.session.close()

    # --- User Settings ---
    def get_user_settings(self, user_id: str) -> Dict[str, str]:
        query = text("SELECT key, value FROM user_settings WHERE user_id = :user_id")
        result = self.session.execute(query, {"user_id": user_id})
        return {row[0]: row[1] for row in result.fetchall()}

    def update_user_setting(self, user_id: str, key: str, value: str):
        query = text("""
        INSERT INTO user_settings (id, user_id, key, value, updated_at)
        VALUES (:id, :user_id, :key, :value, :updated_at)
        ON CONFLICT(user_id, key) DO UPDATE SET value = :value, updated_at = :updated_at
        """)
        self.session.execute(query, {
            "id": str(uuid.uuid4()), "user_id": user_id, "key": key,
            "value": value, "updated_at": int(datetime.now().timestamp())
        })
        self.session.commit()

    # --- Global Settings (admin only) ---
    def get_global_setting(self, key: str, default: str = "") -> str:
        query = text("SELECT value FROM settings WHERE key = :key")
        result = self.session.execute(query, {"key": key})
        row = result.fetchone()
        return row[0] if row else default

    def get_all_settings(self) -> Dict[str, str]:
        query = text("SELECT key, value FROM settings")
        result = self.session.execute(query)
        return {row[0]: row[1] for row in result.fetchall()}

    def update_setting(self, key: str, value: str):
        query = text("""
        INSERT INTO settings (key, value, updated_at)
        VALUES (:key, :value, :updated_at)
        ON CONFLICT(key) DO UPDATE SET value = :value, updated_at = :updated_at
        """)
        self.session.execute(query, {"key": key, "value": value, "updated_at": int(datetime.now().timestamp())})
        self.session.commit()


def get_repository():
    repo = Repository()
    try:
        yield repo
    finally:
        repo.close()
