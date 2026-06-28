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
                    if existing < 32:
                        import time as _time
                        now = int(_time.time())
                        # Delete old system templates and re-seed
                        conn.execute(text("DELETE FROM templates WHERE user_id = 'system'"))
                        seeds = [
                            # ── Message Templates ──
                            ("tpl_system_1", "system", "TikTok Growth — Warm DM", "message_template", "Hey {username}! I came across your profile and really liked your content about {topic}. Would love to connect and see what we can build together!", "tiktok", 1, now, now),
                            ("tpl_system_2", "system", "Generic Outreach DM", "message_template", "Hi {username}! Love what you're posting. I think there's some great synergy between our niches. Let me know if you'd be open to chatting!", None, 1, now, now),
                            ("tpl_system_3", "system", "Comment Engagement Reply", "message_template", "This is such a great point! I've been thinking about this a lot lately. Would love to hear more of your thoughts on this.", None, 0, now, now),
                            ("tpl_system_8", "system", "Warm Tone — Friendly & Authentic", "message_template", "Hey {username}! Just wanted to say I really vibed with your recent post. Your content always hits different. Keep doing what you're doing!", None, 0, now, now),
                            ("tpl_system_9", "system", "Professional Tone — Business Outreach", "message_template", "Hi {username}, I noticed your work in the {niche} space and was impressed by your engagement. I'd love to explore potential collaboration opportunities. Would you be open to a brief chat?", None, 0, now, now),
                            ("tpl_system_11", "system", "Short & Punchy — Hook DM", "message_template", "Yo {username}! Your stuff is fire. Quick question — you open to collabs?", None, 0, now, now),
                            ("tpl_system_12", "system", "Value-First DM — Offer Help", "message_template", "Hey {username}! I noticed you're growing fast in the {niche} space. I put together something that might help you scale even faster — mind if I share?", None, 0, now, now),
                            ("tpl_system_13", "system", "Compliment + Question DM", "message_template", "Hey {username}! Loved your take on {topic}. Been following that space closely — curious, what's been your biggest lesson so far?", None, 0, now, now),
                            ("tpl_system_14", "system", "Mutual Interest DM", "message_template", "Hey {username}! Seems like we're both into {niche}. Always cool finding people on the same wavelength. What got you started?", None, 0, now, now),
                            ("tpl_system_15", "system", "Twitter/X Reply — Engaging Comment", "message_template", "Great thread! The point about {topic} really resonated. I've seen similar patterns in my own experience. Would love to exchange notes.", "twitter", 0, now, now),
                            ("tpl_system_16", "system", "LinkedIn Connection DM", "message_template", "Hi {username}, I came across your profile and was impressed by your background in {niche}. I'm always looking to connect with people doing interesting work in this space. Would love to stay in touch!", "linkedin", 0, now, now),
                            ("tpl_system_17", "system", "Instagram Reply — Story Reaction", "message_template", "This is so relatable! {topic} is something I've been thinking about a lot lately too. Your perspective is refreshing.", "instagram", 0, now, now),
                            ("tpl_system_18", "system", "Follow-Up DM — No Response", "message_template", "Hey {username}! Just circling back on my last message. No pressure at all — just didn't want you to miss it. Hope you're having a great week!", None, 0, now, now),
                            ("tpl_system_19", "system", "Collaboration Pitch DM", "message_template", "Hey {username}! I've been watching your content and I think there's a really natural fit for a collab. I do {niche} content and my audience would love your stuff. Interested?", None, 0, now, now),
                            ("tpl_system_20", "system", "Community Invite DM", "message_template", "Hey {username}! We're building a small community of {niche} creators and I think you'd be a perfect fit. It's free, no strings — just good people sharing ideas. Want in?", None, 0, now, now),

                            # ── AI Instructions ──
                            ("tpl_system_4", "system", "Safe Follower Check (avoid source followers)", "ai_instruction", "Before engaging with any user, verify they are NOT already following the source account. Skip users who are already followers — we want NEW audience reach, not existing fans.\n\nTarget criteria:\n- Active posters with recent content (last 30 days)\n- Genuine engagement (not bot comments)\n- Bio matches our niche\n- No verified accounts (they won't engage back)\n- No private accounts (can't DM them)", None, 1, now, now),
                            ("tpl_system_5", "system", "TikTok Comment Engage — Dance Niche", "ai_instruction", "You are engaging with commenters on a dance/movement creator's TikTok posts.\n\nGoal: Find engaged fans who would benefit from our content.\n\nRules:\n- Only engage with commenters who left genuine, thoughtful comments\n- Skip spam comments (emojis only, 'follow me', etc.)\n- DM should reference their specific comment when possible\n- Keep DMs under 150 characters\n- Be authentic, not salesy\n- If they have < 50 followers, skip (likely inactive)\n- If they have > 100k followers, skip (won't engage back)", "tiktok", 0, now, now),
                            ("tpl_system_6", "system", "Generic Growth — Follow/Unfollow", "ai_instruction", "You are running a follow/unfollow growth campaign.\n\nTarget accounts in the same niche as the source.\n\nRules:\n- Follow users who are actively posting (last 7 days)\n- Skip users with < 10 posts or < 100 followers\n- Skip users with > 50k followers (won't follow back)\n- Skip private accounts\n- Skip accounts with no profile picture\n- Wait 2-3 days before unfollowing if no follow-back\n- Max 50 follows per day to stay under rate limits", None, 0, now, now),
                            ("tpl_system_10", "system", "Instagram Story Engagement", "ai_instruction", "You are engaging with Instagram users via story views and reactions.\n\nGoal: Build familiarity before sending a DM.\n\nSteps:\n1. View their last 3 stories\n2. React to one story with a relevant emoji\n3. Wait 24 hours\n4. If they viewed your profile back, send a DM\n5. If no response after 48 hours, move on\n\nRules:\n- Only engage with accounts that post stories regularly (at least 3x/week)\n- Skip business accounts with > 100k followers\n- Skip accounts with no recent posts (last 30 days)\n- Keep reactions genuine, not generic", "instagram", 0, now, now),
                            ("tpl_system_21", "system", "TikTok Viral Comment Strategy", "ai_instruction", "You are targeting commenters on viral TikTok posts (100k+ views) in the {niche} niche.\n\nGoal: Get visibility by replying to top comments, then DM engaged users.\n\nStrategy:\n1. Find posts with 100k+ views in target niche\n2. Identify commenters with 500+ likes on their comment\n3. Reply to their comment with something insightful\n4. Wait 6 hours for notification to be seen\n5. DM them referencing the comment thread\n\nRules:\n- Only target comments from the last 48 hours\n- Skip creator accounts (they won't engage)\n- Skip accounts with > 500k followers\n- DM must reference the specific comment they made\n- Max 20 comment replies per hour", "tiktok", 0, now, now),
                            ("tpl_system_22", "system", "Twitter/X Thread Engagement", "ai_instruction", "You are engaging with Twitter/X users who post threads in the {niche} space.\n\nGoal: Build relationships through thoughtful replies before DMing.\n\nStrategy:\n1. Find users posting threads (5+ tweets) about {topic}\n2. Reply to the thread with a genuine, insightful take\n3. Like the thread and retweet it\n4. Wait 24 hours\n5. DM them with a follow-up on your reply\n\nRules:\n- Only target threads from the last 7 days\n- Skip accounts with < 100 followers\n- Skip accounts with > 200k followers\n- Replies must add value, not just agree\n- Max 30 thread replies per day", "twitter", 0, now, now),
                            ("tpl_system_23", "system", "LinkedIn B2B Outreach", "ai_instruction", "You are doing B2B outreach on LinkedIn.\n\nTarget: Decision makers and professionals in {niche}.\n\nStrategy:\n1. Connect with people who recently posted about {topic}\n2. Like and comment on their post\n3. Wait 24 hours for connection acceptance\n4. Send a personalized DM referencing their post\n\nRules:\n- Only target posts from the last 7 days\n- Skip recruiters and salespeople (they won't engage)\n- Skip accounts with < 50 connections\n- DM must be professional, not salesy\n- Mention specific details from their post\n- Max 20 connection requests per day", "linkedin", 0, now, now),
                            ("tpl_system_24", "system", "Instagram Reels Comment Engage", "ai_instruction", "You are engaging with commenters on Instagram Reels in the {niche} niche.\n\nGoal: Find engaged users who would benefit from our content.\n\nRules:\n- Only target Reels with 10k+ views\n- Focus on commenters who left thoughtful comments (not just emojis)\n- Skip comments that are just tagging friends\n- Like their comment before DMing\n- DM should reference the Reel topic\n- Skip accounts with < 100 followers\n- Skip accounts with > 100k followers\n- Max 30 engagements per hour", "instagram", 0, now, now),
                            ("tpl_system_25", "system", "Niche Authority — Content Curator", "ai_instruction", "You are positioning the account as a niche authority by engaging with content creators.\n\nGoal: Build a network of creators in {niche} for future collaborations.\n\nStrategy:\n1. Find creators posting about {topic} regularly (3+ times/week)\n2. Engage with their content genuinely (likes, comments, shares)\n3. Wait 1 week of consistent engagement\n4. DM with a collaboration proposal\n\nRules:\n- Only target accounts with 1k-100k followers (micro-influencers)\n- Skip accounts that don't respond to comments\n- Comments must reference specific content details\n- Max 15 new creator connections per week\n- Don't DM until you've engaged with 3+ of their posts", None, 0, now, now),
                            ("tpl_system_26", "system", "Competitor Audience Mining", "ai_instruction", "You are targeting the audience of competitor accounts in the {niche} space.\n\nGoal: Reach users who are already interested in {topic} but haven't found us yet.\n\nStrategy:\n1. Identify 3-5 competitor accounts\n2. Engage with their recent post commenters\n3. These users are pre-qualified (already interested in niche)\n4. DM with a unique value proposition\n\nRules:\n- Skip users who follow multiple competitors (they're already saturated)\n- Skip users who commented more than 7 days ago (not actively engaged)\n- DM must differentiate from competitor's offering\n- Don't mention competitors by name\n- Max 40 DMs per day across all competitor accounts", None, 0, now, now),
                            ("tpl_system_27", "system", "Local Business Outreach", "ai_instruction", "You are targeting local businesses in the {niche} space.\n\nGoal: Connect with business owners for potential partnerships.\n\nRules:\n- Target businesses that post regularly (at least weekly)\n- Skip businesses with < 10 followers (likely inactive)\n- Skip businesses with > 50k followers (too large to engage)\n- DM must reference their specific business or recent post\n- Keep DMs under 100 characters\n- Focus on businesses in specific cities/regions\n- Max 25 DMs per day", None, 0, now, now),
                            ("tpl_system_28", "system", "Creator Collaboration Match", "ai_instruction", "You are finding creators for cross-promotion collaborations.\n\nGoal: Find creators with similar audience size for mutual growth.\n\nStrategy:\n1. Find creators with follower count within 50% of ours\n2. Check their engagement rate (likes/views ratio)\n3. Engage with 2-3 of their recent posts\n4. DM with a specific collaboration idea\n\nRules:\n- Only target accounts with 1k-50k followers\n- Skip accounts with < 2% engagement rate\n- Skip accounts that don't reply to comments\n- DM must include a specific collaboration proposal\n- Mention their content that inspired the collab idea\n- Max 10 collaboration pitches per week", None, 0, now, now),

                            # ── Bot Instructions ──
                            ("tpl_system_7", "system", "Bot Safety — Skip Verified & Bots", "bot_instruction", "SAFETY RULES (always follow):\n1. Never engage with verified accounts (blue checkmark)\n2. Never engage with accounts that have 0 posts\n3. Never engage with accounts created in the last 7 days\n4. Never engage with accounts that have no profile picture\n5. Never engage with accounts whose bio contains 'follow for follow', 'f4f', 'l4l', 'bot', 'spam'\n6. If the account is already following the source, skip them\n7. If the account has been contacted before by ANY campaign, skip them\n8. Rate limit: max 50 actions per day, min 60 seconds between actions", None, 1, now, now),
                            ("tpl_system_29", "system", "Conservative Safety — Low Risk", "bot_instruction", "ULTRA-SAFE MODE — Use when account is new or recovering from a ban:\n\n1. Max 20 actions per day (reduced from 50)\n2. Min 120 seconds between actions\n3. Never engage with accounts < 30 days old\n4. Never engage with accounts < 50 followers\n5. Never engage with accounts > 100k followers\n6. Skip ALL private accounts\n7. Skip ALL verified accounts\n8. Skip accounts with no bio\n9. Skip accounts with no profile picture\n10. Skip accounts whose bio contains ANY of: 'follow for follow', 'f4f', 'l4l', 'bot', 'spam', 'giveaway', 'free', 'winner'\n11. If account has been contacted before, skip permanently\n12. Take 5-minute breaks every 10 actions", None, 0, now, now),
                            ("tpl_system_30", "system", "Aggressive Safety — High Volume", "bot_instruction", "HIGH-VOLUME MODE — Use only with warmed-up accounts:\n\n1. Max 100 actions per day\n2. Min 30 seconds between actions\n3. Skip verified accounts\n4. Skip accounts with 0 posts\n5. Skip accounts with no profile picture\n6. Skip accounts contacted in the last 7 days\n7. Skip accounts whose bio contains 'follow for follow', 'f4f', 'l4l', 'bot', 'spam'\n8. Take 10-minute breaks every 50 actions\n9. Vary action timing (randomize delays)\n10. Never perform the same action type more than 3x in a row", None, 0, now, now),
                            ("tpl_system_31", "system", "Niche Filter — Skip Off-Topic", "bot_instruction", "NICHE FILTERING — Skip users whose content doesn't match our niche:\n\n1. Check if user's bio mentions keywords related to {niche}\n2. Check if user's recent posts are about {topic}\n3. Skip if bio is empty or generic (no niche signals)\n4. Skip if recent posts are about unrelated topics\n5. Skip if user follows mostly accounts outside our niche\n6. Prioritize users who post about {topic} regularly\n7. Prioritize users who engage with niche-specific content\n8. If uncertain, include (better to reach than miss)", None, 0, now, now),
                            ("tpl_system_32", "system", "Engagement Quality Filter", "bot_instruction", "ENGAGEMENT QUALITY — Only engage with users who have genuine engagement:\n\n1. Skip users whose comments are all < 5 words\n2. Skip users whose comments are just emojis\n3. Skip users whose comments contain 'follow me', 'check my profile', 'DM for collab'\n4. Skip users who comment on > 50 posts per day (likely bots)\n5. Prioritize users who leave thoughtful, specific comments\n6. Prioritize users who reply to other commenters\n7. Prioritize users whose comments get likes from others\n8. If user has > 10% of comments flagged as spam, skip entirely", None, 0, now, now),
                        ]
                        for s in seeds:
                            conn.execute(text(
                                "INSERT OR IGNORE INTO templates (id, user_id, name, template_type, content, platform, is_default, created_at, updated_at) "
                                "VALUES (:id, :user_id, :name, :template_type, :content, :platform, :is_default, :created_at, :updated_at)"
                            ), {"id": s[0], "user_id": s[1], "name": s[2], "template_type": s[3], "content": s[4], "platform": s[5], "is_default": s[6], "created_at": s[7], "updated_at": s[8]})
                        conn.commit()
                        logging.info(f"Seeded {len(seeds)} default templates.")

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
