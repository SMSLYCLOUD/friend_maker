import sqlite3
import logging
from pathlib import Path
from app.config import settings

def _resolve_db_path() -> Path:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        return Path(db_url.removeprefix("sqlite:///"))
    return settings.DATA_DIR / settings.DB_NAME

DB_PATH = _resolve_db_path()

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Initialize the database and run migrations."""
    from .migrations import SCHEMA

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executescript(SCHEMA)
        conn.commit()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
