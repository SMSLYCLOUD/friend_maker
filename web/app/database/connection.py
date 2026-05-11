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
            # Migration check: Add password column if it doesn't exist
            # Note: PRAGMA table_info is specific to SQLite. For Postgres, we'd check information_schema.
            if settings.DATABASE_URL.startswith("sqlite"):
                cursor = conn.execute(text("PRAGMA table_info(accounts)"))
                columns = [row[1] for row in cursor.fetchall()]
                if 'password' not in columns:
                    conn.execute(text("ALTER TABLE accounts ADD COLUMN password TEXT"))
                    conn.commit()
                    logging.info("Migration: Added password column to accounts.")
                
                # Check for ai_instructions in campaigns
                cursor = conn.execute(text("PRAGMA table_info(campaigns)"))
                columns = [row[1] for row in cursor.fetchall()]
                if 'ai_instructions' not in columns:
                    conn.execute(text("ALTER TABLE campaigns ADD COLUMN ai_instructions TEXT"))
                    conn.commit()
                    logging.info("Migration: Added ai_instructions column to campaigns.")

            # We use raw SQL for migrations to keep it simple for now
            # Note: Postgres doesn't support 'executescript' like sqlite3, so we split by semicolon
            for statement in SCHEMA.split(';'):
                if statement.strip():
                    conn.execute(text(statement))
            conn.commit()
            logging.info("Database initialized successfully.")
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
