"""
Central config. Anything tunable lives here so you never hunt through
the codebase looking for magic strings.
"""
import os

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

# Storage
DB_PATH = os.environ.get("DB_PATH", "tickets.db")

# Which fields we treat as "verifiable" and will diff on every visit.
# Add/remove fields here -- the diff engine reads this list directly.
VERIFIABLE_FIELDS = [
    "full_name",
    "email",
    "phone",
    "address",
    "employer",
    "verified_status",
]

# Safety cap on the agent loop to prevent runaway tool-calling.
AGENT_MAX_ITERATIONS = 10
