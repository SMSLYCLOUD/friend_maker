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

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
