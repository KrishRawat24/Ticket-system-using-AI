"""
Agent tools.

Each tool is a normal Python function PLUS a JSON schema describing
how Claude should invoke it. The schemas are sent with every API call;
TOOL_REGISTRY maps the names Claude uses to the actual callables.

To add a new tool:
1. Write the function
2. Add a schema entry to TOOL_SCHEMAS
3. Register it in TOOL_REGISTRY at the bottom
"""
from datetime import datetime
from typing import Any

from . import core, db


def get_ticket(ticket_id: str) -> dict:
    """Tool: fetch full ticket including parsed diff."""
    ticket = core.get_ticket(ticket_id)
    return ticket or {"error": "ticket not found"}


def get_user_history(user_id: str) -> dict:
    """Tool: return up to 10 past tickets for this user (pattern detection)."""
    tickets = db.query(
        "SELECT ticket_id, ticket_type, severity, ai_classification, "
        "created_at, status "
        "FROM tickets WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT 10",
        (user_id,),
    )
    return {"count": len(tickets), "tickets": tickets}


def update_ticket(
    ticket_id: str,
    classification: str,
    summary: str,
    suggested_action: str,
    severity: str,
    status: str,
) -> dict:
    """Tool: write the agent's analysis back to the ticket."""
    resolved_at = datetime.utcnow().isoformat() if status == "resolved" else None
    db.query(
        """UPDATE tickets
           SET ai_classification = ?, ai_summary = ?, ai_suggested_action = ?,
               severity = ?, status = ?, resolved_at = ?
           WHERE ticket_id = ?""",
        (
            classification,
            summary,
            suggested_action,
            severity,
            status,
            resolved_at,
            ticket_id,
        ),
        fetch=None,
    )
    return {"ok": True, "ticket_id": ticket_id, "new_status": status}


def update_baseline(user_id: str, accepted_diff: dict) -> dict:
    """Tool: refresh baseline after accepting a legitimate change."""
    baseline = core.get_baseline(user_id)
    if not baseline:
        return {"error": "no baseline to update"}
    new_data = dict(baseline["data"])
    for field, change in accepted_diff.items():
        new_data[field] = change["new"]
    core.save_snapshot(user_id, new_data)
    return {"ok": True, "fields_updated": list(accepted_diff.keys())}


# JSON schemas sent to Claude with every API call.
# Field descriptions matter -- Claude reads them to decide HOW to call.
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_ticket",
        "description": (
            "Fetch full details of a ticket including the diff between "
            "saved and fresh data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
    },
    {
        "name": "get_user_history",
        "description": (
            "Get the user's last 10 tickets to detect patterns "
            "(repeat discrepancies often indicate fraud)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "update_ticket",
        "description": (
            "Write your final analysis. "
            "classification: 'legitimate_change' | 'data_error' | "
            "'fraud_signal' | 'third_party_error' | 'no_change'. "
            "severity: 'low' | 'medium' | 'high'. "
            "status: 'resolved' (auto-close) | 'in_review' (needs human) | "
            "'escalated' (urgent)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "classification": {"type": "string"},
                "summary": {
                    "type": "string",
                    "description": "1-2 plain-English sentences for a human reviewer.",
                },
                "suggested_action": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "status": {
                    "type": "string",
                    "enum": ["resolved", "in_review", "escalated"],
                },
            },
            "required": [
                "ticket_id",
                "classification",
                "summary",
                "suggested_action",
                "severity",
                "status",
            ],
        },
    },
    {
        "name": "update_baseline",
        "description": (
            "Refresh the saved baseline with new data after confirming "
            "the change is legitimate. Call this ONLY after update_ticket "
            "with classification='legitimate_change'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "accepted_diff": {
                    "type": "object",
                    "description": "Same shape as the ticket's diff field.",
                },
            },
            "required": ["user_id", "accepted_diff"],
        },
    },
]

# Name-to-callable map used by the agent loop.
TOOL_REGISTRY = {
    "get_ticket": get_ticket,
    "get_user_history": get_user_history,
    "update_ticket": update_ticket,
    "update_baseline": update_baseline,
}
