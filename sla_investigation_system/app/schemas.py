from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class TicketCreate(BaseModel):
    ticket_code: str
    subject: str
    description: str
    priority: str
    category: str
    asset_code: str | None = None
    status: str = "Open"
    created_at: datetime

class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_code: str
    subject: str
    description: str
    priority: str
    category: str
    status: str
    created_at: datetime
    asset_id: int | None

class ChatRequest(BaseModel):
    question: str = Field(min_length=1)

class InvestigationOut(BaseModel):
    risk_assessment: str
    sla: dict
    supporting_evidence: list[str]
    similar_incidents: list[dict]
    recommended_actions: list[str]
    applicable_policies: list[dict]
    missing_information: list[str]
    limitations: list[str]
    conflicts: list[str]
