"""
HTTP layer. Three endpoints:

    POST /process          -> run the full pipeline for one user
    GET  /tickets/{id}     -> read a ticket
    GET  /health           -> liveness probe

The orchestrator (process_request) is the public entry point that ties
deterministic core + agentic AI together.
"""
import logging

from fastapi import FastAPI, HTTPException

from . import core, third_party, agent, db
from .models import ProcessRequest, TicketResponse


log = logging.getLogger(__name__)

app = FastAPI(title="Ticket System with Agentic AI", version="1.0")


@app.on_event("startup")
def _startup():
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process", response_model=TicketResponse)
def process(req: ProcessRequest):
    """
    Full pipeline:
      1. Resolve external_id -> internal user_id
      2. Fetch fresh data from third party
      3. Diff against baseline (or create one on first visit)
      4. Create a ticket
      5. Hand it to the AI agent
      6. Return the final state
    """
    try:
        result = process_request(req.external_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str):
    ticket = core.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    return ticket


def process_request(external_id: str) -> dict:
    """
    The orchestrator. This is what the HTTP route calls, but you can also
    invoke it from a queue worker, cron job, CLI, or test.
    """
    user_id = core.get_or_create_user(external_id)
    fresh_data = third_party.fetch(external_id)
    baseline = core.get_baseline(user_id)

    if baseline is None:
        # FIRST VISIT
        core.save_snapshot(user_id, fresh_data)
        ticket_id = core.create_ticket(user_id, "onboarding", diff=None)
        log.info("new user %s -> ticket %s", external_id, ticket_id)
    else:
        # RETURN VISIT
        diff = core.compare_records(baseline["data"], fresh_data)
        if diff:
            ticket_id = core.create_ticket(user_id, "discrepancy", diff=diff)
            log.info("diff for %s -> ticket %s (%s)",
                     external_id, ticket_id, list(diff.keys()))
        else:
            ticket_id = core.create_ticket(user_id, "verified", diff=None)
            log.info("verified %s -> ticket %s", external_id, ticket_id)

    # Hand to AI agent
    agent_result = agent.run_on_ticket(ticket_id, user_id)

    # Return the final ticket state with agent metadata
    final = core.get_ticket(ticket_id)
    final["agent_iterations"] = agent_result["iterations"]
    return final
