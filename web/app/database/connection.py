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
            if settings.DATABASE_URL.startswith("sqlite"):
                # Check if accounts table exists before migrating
                cursor = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"))
                if cursor.fetchone():
                    # Table exists — run column migrations
                    cursor = conn.execute(text("PRAGMA table_info(accounts)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'password' not in columns:
                        conn.execute(text("ALTER TABLE accounts ADD COLUMN password TEXT"))
                        conn.commit()
                        logging.info("Migration: Added password column to accounts.")

                    cursor = conn.execute(text("PRAGMA table_info(campaigns)"))
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'ai_instructions' not in columns:
                        conn.execute(text("ALTER TABLE campaigns ADD COLUMN ai_instructions TEXT"))
                        conn.commit()
                        logging.info("Migration: Added ai_instructions column to campaigns.")
                else:
                    # Table doesn't exist — create schema from scratch
                    for statement in SCHEMA.split(';'):
                        if statement.strip():
                            conn.execute(text(statement))
                    conn.commit()
                    logging.info("Database schema created.")

            else:
                for statement in SCHEMA.split(';'):
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()
            logging.info("Database initialized successfully.")
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
