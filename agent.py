"""
The agentic AI loop.

This is the ONLY module that talks to Anthropic. Every other module is
pure Python / SQL. If you want to swap models or providers, you only
touch this file.

How the loop works:
    1. We send Claude the ticket context + the list of tools
    2. Claude responds with EITHER:
       - stop_reason == 'end_turn' (done) -> we return the final text
       - stop_reason == 'tool_use'        -> Claude wants to call tools
    3. If tools were called, we execute each one and feed results back
    4. Repeat until Claude is done, or we hit AGENT_MAX_ITERATIONS
"""
import json
import logging

import anthropic

from .config import ANTHROPIC_API_KEY, MODEL, AGENT_MAX_ITERATIONS
from .tools import TOOL_SCHEMAS, TOOL_REGISTRY


log = logging.getLogger(__name__)

# Singleton client. The SDK is thread-safe.
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """You are a ticket-resolution agent for an identity verification system.

For each ticket:
1. Use get_ticket to read the ticket details and any diff
2. Use get_user_history if you need pattern context (repeated changes can be suspicious)
3. Classify the change:
   - First-visit ticket (no diff)        -> 'no_change', resolved, low severity
   - One-time address/employer change    -> 'legitimate_change', resolved, low severity
   - Status flipping to 'expired'        -> 'third_party_error', in_review, medium severity
   - Repeated diffs across recent visits -> 'fraud_signal', escalated, high severity
   - Format inconsistencies              -> 'data_error', in_review, medium severity
4. Call update_ticket with your decision
5. If classification is 'legitimate_change', also call update_baseline

Be decisive. Auto-resolve clear cases. Escalate only when genuinely ambiguous.
Always finish by calling update_ticket -- a ticket left untouched is a failure."""


def run_on_ticket(ticket_id: str, user_id: str) -> dict:
    """
    Hand a ticket to the AI agent. Returns:
        {
          "final_message": <agent's last text reply>,
          "iterations":    <how many round-trips it took>,
          "tool_calls":    [list of {name, args} for observability]
        }
    """
    messages = [
        {
            "role": "user",
            "content": (
                f"Process ticket {ticket_id} for user {user_id}. "
                "Read it, decide, and update it. Refresh the baseline if appropriate."
            ),
        }
    ]
    tool_call_log: list[dict] = []

    for iteration in range(AGENT_MAX_ITERATIONS):
        response = _client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Done -- Claude returned plain text with no tool calls.
        if response.stop_reason == "end_turn":
            text_parts = [b.text for b in response.content if b.type == "text"]
            return {
                "final_message": "\n".join(text_parts),
                "iterations": iteration + 1,
                "tool_calls": tool_call_log,
            }

        # Otherwise execute every tool Claude requested in this turn.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            log.info("agent calling %s with %s", block.name, block.input)
            tool_call_log.append({"name": block.name, "args": block.input})
            try:
                result = TOOL_REGISTRY[block.name](**block.input)
            except Exception as e:
                log.exception("tool %s failed", block.name)
                result = {"error": str(e)}
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # If we ran out of iterations, something is wrong. Return what we have.
    log.warning("agent hit max iterations on ticket %s", ticket_id)
    return {
        "final_message": "agent hit iteration cap",
        "iterations": AGENT_MAX_ITERATIONS,
        "tool_calls": tool_call_log,
    }
