"""
Database layer. SQLite for portability; swap the connection logic
to talk to Postgres in production -- the rest of the code is agnostic.
"""
import sqlite3
from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    user_id TEXT,
    data TEXT,
    captured_at TEXT,
    is_baseline INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    user_id TEXT,
    ticket_type TEXT,
    status TEXT,
    severity TEXT,
    diff TEXT,
    ai_classification TEXT,
    ai_summary TEXT,
    ai_suggested_action TEXT,
    created_at TEXT,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_baseline
    ON snapshots(user_id, is_baseline);
CREATE INDEX IF NOT EXISTS idx_tickets_user
    ON tickets(user_id);
"""


def init_db() -> None:
    """Create tables if they don't exist. Idempotent."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def query(sql: str, params: tuple = (), fetch: str = "all"):
    """
    Tiny query helper.
    fetch='one' -> dict or None
    fetch='all' -> list of dicts
    fetch=None  -> no return (for writes)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    if fetch == "one":
        row = cur.fetchone()
        result = dict(row) if row else None
    elif fetch == "all":
        result = [dict(r) for r in cur.fetchall()]
    else:
        result = None
    conn.commit()
    conn.close()
    return result
