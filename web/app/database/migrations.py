SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    session_data TEXT,
    proxy_config TEXT,
    is_active INTEGER DEFAULT 1,
    last_action_at INTEGER,
    daily_actions INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    targeting_json TEXT,
    message_template TEXT,
    schedule_json TEXT,
    daily_limit INTEGER DEFAULT 50,
    total_actions INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    platform_user_id TEXT NOT NULL,
    username TEXT,
    profile_json TEXT,
    ai_score REAL,
    status TEXT DEFAULT 'pending',
    processed_at INTEGER
);
CREATE TABLE IF NOT EXISTS action_logs (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    campaign_id TEXT,
    action_type TEXT,
    target_user TEXT,
    success INTEGER,
    error TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
"""
