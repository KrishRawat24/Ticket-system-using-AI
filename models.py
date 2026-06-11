"""
Pydantic models. These define the shape of HTTP requests and responses
so FastAPI can validate inputs and generate OpenAPI docs automatically.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    """Body of POST /process"""
    external_id: str = Field(..., description="Customer identifier in your system")


class TicketResponse(BaseModel):
    """Returned from POST /process and GET /tickets/{id}"""
    ticket_id: str
    user_id: str
    ticket_type: str
    status: str
    severity: Optional[str] = None
    diff: Optional[dict] = None
    ai_classification: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_suggested_action: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None
    agent_iterations: Optional[int] = None
