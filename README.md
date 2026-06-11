# Ticket System with Agentic AI

A ticket system that verifies user data against a third-party API and uses
an AI agent to classify and resolve discrepancies.

## Run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

Then visit http://localhost:8000/docs for the interactive API explorer.

## Try it

```bash
# First visit -- creates a baseline
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"external_id": "user_001"}'

# Second visit -- the agent compares, classifies, decides
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"external_id": "user_001"}'

# Read a ticket later
curl http://localhost:8000/tickets/<ticket_id>
```

## Architecture

```
app/
  config.py        env vars, constants
  db.py            SQLite schema + query helper
  models.py        Pydantic request/response shapes
  third_party.py   external API adapter (mocked)
  core.py          deterministic business logic, NO AI
  tools.py         agent tools + JSON schemas
  agent.py         the agent loop, ONLY file that imports anthropic
  api.py           FastAPI routes + orchestrator
main.py            uvicorn entry point
```

The AI is isolated to `agent.py` and `tools.py`. Everything else is plain
Python and SQL. You can unit-test the core without mocking Claude, and
you can swap models or providers by editing one file.

## How the agent works

1. `process_request()` creates a ticket (deterministic logic)
2. `agent.run_on_ticket()` hands the ticket to Claude
3. Claude calls tools to investigate: `get_ticket`, `get_user_history`
4. Claude decides classification + action and calls `update_ticket`
5. If the change is legitimate, Claude also calls `update_baseline`
6. The loop ends when Claude returns plain text with no more tool calls

A 10-iteration cap prevents runaway loops if the model misbehaves.

## Swapping the third-party API

Edit `app/third_party.py` and replace `fetch()` with a real HTTP call.
The rest of the system needs no changes.
