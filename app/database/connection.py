import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Determine the database URL
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    # Ensure directory exists for sqlite
    from pathlib import Path
    db_path = Path(db_url.removeprefix("sqlite:///"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # SQLite specific args
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    # Postgres or other
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database and run migrations."""
    from .migrations import SCHEMA
    
    with engine.connect() as conn:
        try:
            # Create tables first via SCHEMA
            for statement in SCHEMA.split(';'):
                if statement.strip():
                    conn.execute(text(statement))
            conn.commit()

            # Migration: Add columns if table already existed without them
            if settings.DATABASE_URL.startswith("sqlite"):
                tables = [row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]

                # --- accounts table migrations ---
                if 'accounts' in tables:
                    cursor = conn.execute(text("PRAGMA table_info(accounts)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'password' not in columns:
                        conn.execute(text("ALTER TABLE accounts ADD COLUMN password TEXT"))
                        logging.info("Migration: Added password column to accounts.")
                    if 'user_id' not in columns:
                        conn.execute(text("ALTER TABLE accounts ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"))
                        logging.info("Migration: Added user_id column to accounts.")
                    conn.commit()

                # --- campaigns table migrations ---
                if 'campaigns' in tables:
                    cursor = conn.execute(text("PRAGMA table_info(campaigns)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'ai_instructions' not in columns:
                        conn.execute(text("ALTER TABLE campaigns ADD COLUMN ai_instructions TEXT"))
                        logging.info("Migration: Added ai_instructions column to campaigns.")
                    if 'user_id' not in columns:
                        conn.execute(text("ALTER TABLE campaigns ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"))
                        logging.info("Migration: Added user_id column to campaigns.")
                    conn.commit()

                # --- targets table migrations ---
                if 'targets' in tables:
                    cursor = conn.execute(text("PRAGMA table_info(targets)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'user_id' not in columns:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"))
                        logging.info("Migration: Added user_id column to targets.")
                    if 'comment_id' not in columns:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN comment_id TEXT"))
                        logging.info("Migration: Added comment_id column to targets.")
                    if 'post_url' not in columns:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN post_url TEXT"))
                        logging.info("Migration: Added post_url column to targets.")
                    if 'source_post_url' not in columns:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN source_post_url TEXT"))
                        logging.info("Migration: Added source_post_url column to targets.")
                    conn.commit()

                # --- action_logs table migrations ---
                if 'action_logs' in tables:
                    cursor = conn.execute(text("PRAGMA table_info(action_logs)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'user_id' not in columns:
                        conn.execute(text("ALTER TABLE action_logs ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"))
                        logging.info("Migration: Added user_id column to action_logs.")
                    conn.commit()

                # --- contact_registry table (cross-campaign dedup) ---
                if 'contact_registry' not in tables:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS contact_registry (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            platform TEXT NOT NULL,
                            platform_user_id TEXT NOT NULL,
                            username TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            campaign_id TEXT,
                            contacted_at INTEGER,
                            UNIQUE(user_id, platform, platform_user_id, action_type)
                        )
                    """))
                    logging.info("Migration: Created contact_registry table.")
                    conn.commit()

                # --- Seed default templates ---
                if 'templates' in tables:
                    existing = conn.execute(text("SELECT COUNT(*) FROM templates WHERE user_id = 'system'")).fetchone()[0]
                    if existing == 0:
                        import time as _time
                        now = int(_time.time())
                        seeds = [
                            ("tpl_system_1", "system", "TikTok Growth — Warm DM", "message_template", "Hey {username}! I came across your profile and really liked your content about {topic}. Would love to connect and see what we can build together!", "tiktok", 1, now, now),
                            ("tpl_system_2", "system", "Generic Outreach DM", "message_template", "Hi {username}! Love what you're posting. I think there's some great synergy between our niches. Let me know if you'd be open to chatting!", None, 1, now, now),
                            ("tpl_system_3", "system", "Comment Engagement Reply", "message_template", "This is such a great point! I've been thinking about this a lot lately. Would love to hear more of your thoughts on this.", None, 0, now, now),
                            ("tpl_system_4", "system", "Safe Follower Check (avoid source followers)", "ai_instruction", "Before engaging with any user, verify they are NOT already following the source account. Skip users who are already followers — we want NEW audience reach, not existing fans.\n\nTarget criteria:\n- Active posters with recent content (last 30 days)\n- Genuine engagement (not bot comments)\n- Bio matches our niche\n- No verified accounts (they won't engage back)\n- No private accounts (can't DM them)", None, 1, now, now),
                            ("tpl_system_5", "system", "TikTok Comment Engage — Dance Niche", "ai_instruction", "You are engaging with commenters on a dance/movement creator's TikTok posts.\n\nGoal: Find engaged fans who would benefit from our content.\n\nRules:\n- Only engage with commenters who left genuine, thoughtful comments\n- Skip spam comments (emojis only, 'follow me', etc.)\n- DM should reference their specific comment when possible\n- Keep DMs under 150 characters\n- Be authentic, not salesy\n- If they have < 50 followers, skip (likely inactive)\n- If they have > 100k followers, skip (won't engage back)", "tiktok", 0, now, now),
                            ("tpl_system_6", "system", "Generic Growth — Follow/Unfollow", "ai_instruction", "You are running a follow/unfollow growth campaign.\n\nTarget accounts in the same niche as the source.\n\nRules:\n- Follow users who are actively posting (last 7 days)\n- Skip users with < 10 posts or < 100 followers\n- Skip users with > 50k followers (won't follow back)\n- Skip private accounts\n- Skip accounts with no profile picture\n- Wait 2-3 days before unfollowing if no follow-back\n- Max 50 follows per day to stay under rate limits", None, 0, now, now),
                            ("tpl_system_7", "system", "Bot Safety — Skip Verified & Bots", "bot_instruction", "SAFETY RULES (always follow):\n1. Never engage with verified accounts (blue checkmark)\n2. Never engage with accounts that have 0 posts\n3. Never engage with accounts created in the last 7 days\n4. Never engage with accounts that have no profile picture\n5. Never engage with accounts whose bio contains 'follow for follow', 'f4f', 'l4l', 'bot', 'spam'\n6. If the account is already following the source, skip them\n7. If the account has been contacted before by ANY campaign, skip them\n8. Rate limit: max 50 actions per day, min 60 seconds between actions", None, 1, now, now),
                            ("tpl_system_8", "system", "Warm Tone — Friendly & Authentic", "message_template", "Hey {username}! Just wanted to say I really vibed with your recent post. Your content always hits different. Keep doing what you're doing!", None, 0, now, now),
                            ("tpl_system_9", "system", "Professional Tone — Business Outreach", "message_template", "Hi {username}, I noticed your work in the {niche} space and was impressed by your engagement. I'd love to explore potential collaboration opportunities. Would you be open to a brief chat?", None, 0, now, now),
                            ("tpl_system_10", "system", "Instagram Story Engagement", "ai_instruction", "You are engaging with Instagram users via story views and reactions.\n\nGoal: Build familiarity before sending a DM.\n\nSteps:\n1. View their last 3 stories\n2. React to one story with a relevant emoji\n3. Wait 24 hours\n4. If they viewed your profile back, send a DM\n5. If no response after 48 hours, move on\n\nRules:\n- Only engage with accounts that post stories regularly (at least 3x/week)\n- Skip business accounts with > 100k followers\n- Skip accounts with no recent posts (last 30 days)\n- Keep reactions genuine, not generic", "instagram", 0, now, now),
                        ]
                        for s in seeds:
                            conn.execute(text(
                                "INSERT OR IGNORE INTO templates (id, user_id, name, template_type, content, platform, is_default, created_at, updated_at) "
                                "VALUES (:id, :user_id, :name, :template_type, :content, :platform, :is_default, :created_at, :updated_at)"
                            ), {"id": s[0], "user_id": s[1], "name": s[2], "template_type": s[3], "content": s[4], "platform": s[5], "is_default": s[6], "created_at": s[7], "updated_at": s[8]})
                        conn.commit()
                        logging.info("Seeded 10 default templates.")

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
