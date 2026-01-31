import sqlite3
import logging
from pathlib import Path

DB_PATH = Path("social_growth.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
