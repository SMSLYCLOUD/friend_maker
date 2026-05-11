import json
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import text
from app.database.connection import SessionLocal
from app.database.models import Account, Campaign, Target, ActionLog
from app.utils.crypto import crypto

class Repository:
    def __init__(self):
        self.session = SessionLocal()

    def _row_to_dict(self, row) -> dict:
        return row._asdict() if hasattr(row, '_asdict') else dict(row)

    # --- User Operations ---
    def create_user(self, username: str, password_hash: str):
        query = text("INSERT INTO users (id, username, hashed_password, created_at) VALUES (:id, :username, :password, :created_at)")
        self.session.execute(query, {
            "id": str(uuid.uuid4()), 
            "username": username, 
            "password": password_hash,
            "created_at": int(time.time())
        })
        self.session.commit()

    def get_user(self, username: str):
        query = text("SELECT * FROM users WHERE username = :username")
        result = self.session.execute(query, {"username": username})
        row = result.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    # --- Account Operations ---
    def create_account(self, account: Account) -> Account:
        query = text("""
        INSERT INTO accounts (id, platform, username, password, display_name, session_data, proxy_config, is_active, created_at)
        VALUES (:id, :platform, :username, :password, :display_name, :session_data, :proxy_config, :is_active, :created_at)
        """)
        encrypted_session = crypto.encrypt(account.session_data) if account.session_data else None
        encrypted_password = crypto.encrypt(account.password) if account.password else None

        self.session.execute(query, {
            "id": account.id, "platform": account.platform, "username": account.username, 
            "password": encrypted_password,
            "display_name": account.display_name, "session_data": encrypted_session, 
            "proxy_config": account.proxy_config, "is_active": 1 if account.is_active else 0,
            "created_at": account.created_at
        })
        self.session.commit()
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        query = text("SELECT * FROM accounts WHERE id = :id")
        result = self.session.execute(query, {"id": account_id})
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

    def list_accounts(self) -> List[Account]:
        query = text("SELECT * FROM accounts")
        result = self.session.execute(query)
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

    def update_account_session(self, account_id: str, session_data: str):
        query = text("UPDATE accounts SET session_data = :data WHERE id = :id")
        encrypted = crypto.encrypt(session_data)
        self.session.execute(query, {"data": encrypted, "id": account_id})
        self.session.commit()

    # --- Campaign Operations ---
    def create_campaign(self, campaign: Campaign) -> Campaign:
        query = text("""
        INSERT INTO campaigns (id, account_id, name, campaign_type, status, targeting_json, message_template, ai_instructions, schedule_json, daily_limit, created_at)
        VALUES (:id, :account_id, :name, :campaign_type, :status, :targeting_json, :message_template, :ai_instructions, :schedule_json, :daily_limit, :created_at)
        """)
        self.session.execute(query, {
            "id": campaign.id, "account_id": campaign.account_id, "name": campaign.name, 
            "campaign_type": campaign.campaign_type, "status": campaign.status, 
            "targeting_json": campaign.targeting_json, "message_template": campaign.message_template, 
            "ai_instructions": campaign.ai_instructions,
            "schedule_json": campaign.schedule_json, "daily_limit": campaign.daily_limit, 
            "created_at": campaign.created_at
        })
        self.session.commit()
        return campaign

        return Campaign(**self._row_to_dict(row))

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
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
        WHERE id = :id
        """)
        self.session.execute(query, {
            "status": campaign.status, "targeting": campaign.targeting_json, 
            "template": campaign.message_template, "ai": campaign.ai_instructions,
            "schedule": campaign.schedule_json, "limit": campaign.daily_limit,
            "total": campaign.total_actions, "id": campaign.id
        })
        self.session.commit()

    def list_campaigns(self) -> List[Campaign]:
        query = text("SELECT * FROM campaigns ORDER BY created_at DESC")
        result = self.session.execute(query)
        return [Campaign(**self._row_to_dict(row)) for row in result.fetchall()]

    # --- Target Operations ---
    def add_target(self, target: Target):
        # Postgres doesn't have INSERT OR IGNORE, but SQLAlchemy core can handle it or we use raw SQL with ON CONFLICT
        # To stay cross-compatible, we'll check existence first or use ON CONFLICT for Postgres
        query = text("""
        INSERT INTO targets (id, campaign_id, platform_user_id, username, profile_json, status)
        VALUES (:id, :campaign_id, :platform_user_id, :username, :profile_json, :status)
        ON CONFLICT DO NOTHING
        """)
        # Note: SQLite supports ON CONFLICT since 3.24.0. For older sqlite, we'd need a different approach.
        # But Grid/Modern OS should be fine.
        self.session.execute(query, {
            "id": target.id, "campaign_id": target.campaign_id, "platform_user_id": target.platform_user_id,
            "username": target.username, "profile_json": target.profile_json, "status": target.status
        })
        self.session.commit()

    def get_pending_targets(self, campaign_id: str, limit: int = 10) -> List[Target]:
        query = text("SELECT * FROM targets WHERE campaign_id = :id AND status = 'pending' LIMIT :limit")
        result = self.session.execute(query, {"id": campaign_id, "limit": limit})
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
        INSERT INTO action_logs (id, account_id, campaign_id, action_type, target_user, success, error, created_at)
        VALUES (:id, :account_id, :campaign_id, :action_type, :target_user, :success, :error, :created_at)
        """)
        self.session.execute(query, {
            "id": log.id, "account_id": log.account_id, "campaign_id": log.campaign_id, 
            "action_type": log.action_type, "target_user": log.target_user, 
            "success": 1 if log.success else 0, "error": log.error, "created_at": log.created_at
        })
        self.session.commit()

    def get_analytics_summary(self):
        """Returns dictionary with summary stats."""
        # Total Actions
        total_actions = self.session.execute(text("SELECT COUNT(*) FROM action_logs")).scalar() or 0

        # Actions Today
        # Postgres and SQLite have different date functions. We'll use epoch time which is common.
        now = int(time.time())
        day_ago = now - 86400
        today_actions = self.session.execute(text("SELECT COUNT(*) FROM action_logs WHERE created_at > :start"), {"start": day_ago}).scalar() or 0

        # Success Rate
        res = self.session.execute(text("SELECT AVG(CAST(success AS FLOAT)) FROM action_logs")).scalar()
        success_rate = round(res * 100, 1) if res is not None else 0.0

        return {
            "total_actions": total_actions,
            "today_actions": today_actions,
            "success_rate": success_rate
        }

    def close(self):
        self.session.close()

    # --- Settings Operations ---
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
