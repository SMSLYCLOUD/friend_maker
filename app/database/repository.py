import json
import sqlite3
from typing import List, Optional
from app.database.connection import get_connection
from app.database.models import Account, Campaign, Target, ActionLog
from app.utils.crypto import crypto

class Repository:
    def __init__(self):
        self.conn = get_connection()

    def _row_to_dict(self, row) -> dict:
        return dict(row)

    # --- Account Operations ---
    def create_account(self, account: Account) -> Account:
        query = """
        INSERT INTO accounts (id, platform, username, display_name, session_data, proxy_config, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        encrypted_session = crypto.encrypt(account.session_data) if account.session_data else None

        self.conn.execute(query, (
            account.id, account.platform, account.username, account.display_name,
            encrypted_session, account.proxy_config, 1 if account.is_active else 0,
            account.created_at
        ))
        self.conn.commit()
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        query = "SELECT * FROM accounts WHERE id = ?"
        cursor = self.conn.execute(query, (account_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = self._row_to_dict(row)
        # Decrypt session data
        if data['session_data']:
            data['session_data'] = crypto.decrypt(data['session_data'])

        # SQLite stores booleans as integers
        data['is_active'] = bool(data['is_active'])

        return Account(**data)

    def list_accounts(self) -> List[Account]:
        query = "SELECT * FROM accounts"
        cursor = self.conn.execute(query)
        accounts = []
        for row in cursor.fetchall():
            data = self._row_to_dict(row)
            if data['session_data']:
                data['session_data'] = crypto.decrypt(data['session_data'])
            data['is_active'] = bool(data['is_active'])
            accounts.append(Account(**data))
        return accounts

    def update_account_session(self, account_id: str, session_data: str):
        query = "UPDATE accounts SET session_data = ? WHERE id = ?"
        encrypted = crypto.encrypt(session_data)
        self.conn.execute(query, (encrypted, account_id))
        self.conn.commit()

    # --- Campaign Operations ---
    def create_campaign(self, campaign: Campaign) -> Campaign:
        query = """
        INSERT INTO campaigns (id, account_id, name, campaign_type, status, targeting_json, message_template, schedule_json, daily_limit, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (
            campaign.id, campaign.account_id, campaign.name, campaign.campaign_type,
            campaign.status, campaign.targeting_json, campaign.message_template,
            campaign.schedule_json, campaign.daily_limit, campaign.created_at
        ))
        self.conn.commit()
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        query = "SELECT * FROM campaigns WHERE id = ?"
        cursor = self.conn.execute(query, (campaign_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Campaign(**self._row_to_dict(row))

    # --- Target Operations ---
    def add_target(self, target: Target):
        query = """
        INSERT OR IGNORE INTO targets (id, campaign_id, platform_user_id, username, profile_json, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (
            target.id, target.campaign_id, target.platform_user_id,
            target.username, target.profile_json, target.status
        ))
        self.conn.commit()

    def get_pending_targets(self, campaign_id: str, limit: int = 10) -> List[Target]:
        query = "SELECT * FROM targets WHERE campaign_id = ? AND status = 'pending' LIMIT ?"
        cursor = self.conn.execute(query, (campaign_id, limit))
        return [Target(**self._row_to_dict(row)) for row in cursor.fetchall()]

    def update_target_status(self, target_id: str, status: str, ai_score: float = None):
        if ai_score is not None:
            query = "UPDATE targets SET status = ?, ai_score = ? WHERE id = ?"
            self.conn.execute(query, (status, ai_score, target_id))
        else:
            query = "UPDATE targets SET status = ? WHERE id = ?"
            self.conn.execute(query, (status, target_id))
        self.conn.commit()

    # --- Action Logs ---
    def log_action(self, log: ActionLog):
        query = """
        INSERT INTO action_logs (id, account_id, campaign_id, action_type, target_user, success, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (
            log.id, log.account_id, log.campaign_id, log.action_type,
            log.target_user, 1 if log.success else 0, log.error, log.created_at
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()
