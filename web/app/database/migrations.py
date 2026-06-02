SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER
);
CREATE TABLE IF NOT EXISTS user_settings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    updated_at INTEGER,
    UNIQUE(user_id, key)
);
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT,
    display_name TEXT,
    session_data TEXT,
    proxy_config TEXT,
    is_active INTEGER DEFAULT 1,
    last_action_at INTEGER,
    daily_actions INTEGER DEFAULT 0,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    account_id TEXT,
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    targeting_json TEXT,
    message_template TEXT,
    ai_instructions TEXT,
    schedule_json TEXT,
    daily_limit INTEGER DEFAULT 50,
    total_actions INTEGER DEFAULT 0,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    campaign_id TEXT,
    platform_user_id TEXT NOT NULL,
    username TEXT,
    profile_json TEXT,
    ai_score REAL,
    status TEXT DEFAULT 'pending',
    processed_at INTEGER,
    comment_id TEXT,
    post_url TEXT,
    source_post_url TEXT
);
CREATE TABLE IF NOT EXISTS action_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    account_id TEXT,
    campaign_id TEXT,
    action_type TEXT,
    target_user TEXT,
    success INTEGER,
    error TEXT,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS conversation_memory (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    target_user TEXT NOT NULL,
    message TEXT,
    response TEXT,
    timestamp INTEGER,
    metadata TEXT
);
CREATE TABLE IF NOT EXISTS relationship_tracker (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    target_user TEXT NOT NULL,
    interaction_count INTEGER DEFAULT 0,
    last_interaction INTEGER,
    last_interaction_type TEXT,
    metadata TEXT
);
CREATE TABLE IF NOT EXISTS scheduled_actions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_user TEXT,
    parameters TEXT,
    cron_expression TEXT,
    start_time INTEGER,
    end_time INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at INTEGER,
    last_run_at INTEGER
);
"""
