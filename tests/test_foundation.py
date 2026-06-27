import os
import sqlite3
import pytest
from app.database.connection import init_db, get_connection, DB_PATH
from app.utils.crypto import crypto

def setup_module():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def teardown_module():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists("secret.key"):
        os.remove("secret.key")

def test_crypto():
    original_text = "my_secret_password"
    encrypted = crypto.encrypt(original_text)
    assert encrypted != original_text
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == original_text

def test_database_init():
    init_db()
    assert os.path.exists(DB_PATH)

    conn = get_connection()
    cursor = conn.cursor()

    # Check tables
    tables = ["settings", "accounts", "campaigns", "targets", "action_logs"]
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        assert cursor.fetchone() is not None

    conn.close()
