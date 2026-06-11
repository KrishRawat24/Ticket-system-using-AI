"""
Core deterministic business logic. No AI here.

Keeping this pure means you can unit-test it without mocking the LLM,
and you can audit it without worrying about model behavior.
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from . import db
from .config import VERIFIABLE_FIELDS


def get_or_create_user(external_id: str) -> str:
    """Return internal user_id. Create on first sight."""
    existing = db.query(
        "SELECT user_id FROM users WHERE external_id = ?",
        (external_id,),
        fetch="one",
    )
    if existing:
        return existing["user_id"]
    user_id = str(uuid.uuid4())
    db.query(
        "INSERT INTO users (user_id, external_id, created_at) VALUES (?, ?, ?)",
        (user_id, external_id, datetime.utcnow().isoformat()),
        fetch=None,
    )
    return user_id


def get_baseline(user_id: str) -> Optional[dict]:
    """Latest baseline snapshot, or None on first visit."""
    row = db.query(
        "SELECT * FROM snapshots WHERE user_id = ? AND is_baseline = 1 "
        "ORDER BY captured_at DESC LIMIT 1",
        (user_id,),
        fetch="one",
    )
    if not row:
        return None
    return {"snapshot_id": row["snapshot_id"], "data": json.loads(row["data"])}


def save_snapshot(user_id: str, data: dict) -> str:
    """
    Save a new baseline. Marks any previous baseline as non-current
    so we keep a full historical trail (for audits) while is_baseline=1
    always points to the latest truth.
    """
    db.query(
        "UPDATE snapshots SET is_baseline = 0 WHERE user_id = ?",
        (user_id,),
        fetch=None,
    )
    snapshot_id = str(uuid.uuid4())
    db.query(
        "INSERT INTO snapshots (snapshot_id, user_id, data, captured_at, is_baseline) "
        "VALUES (?, ?, ?, ?, 1)",
        (snapshot_id, user_id, json.dumps(data), datetime.utcnow().isoformat()),
        fetch=None,
    )
    return snapshot_id


def compare_records(saved: dict, fresh: dict) -> dict:
    """Structured diff. Empty dict means no change."""
    diffs = {}
    for field in VERIFIABLE_FIELDS:
        if saved.get(field) != fresh.get(field):
            diffs[field] = {"old": saved.get(field), "new": fresh.get(field)}
    return diffs


def create_ticket(user_id: str, ticket_type: str, diff: Optional[dict]) -> str:
    """Insert a new ticket, status='open'."""
    ticket_id = str(uuid.uuid4())
    db.query(
        """INSERT INTO tickets
           (ticket_id, user_id, ticket_type, status, diff, created_at)
           VALUES (?, ?, ?, 'open', ?, ?)""",
        (
            ticket_id,
            user_id,
            ticket_type,
            json.dumps(diff) if diff else None,
            datetime.utcnow().isoformat(),
        ),
        fetch=None,
    )
    return ticket_id


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Read a ticket, parsing the diff JSON if present."""
    row = db.query(
        "SELECT * FROM tickets WHERE ticket_id = ?",
        (ticket_id,),
        fetch="one",
    )
    if not row:
        return None
    if row.get("diff"):
        row["diff"] = json.loads(row["diff"])
    return row
