from pydantic import BaseModel, Field
from typing import Any

class SearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    document_type: str | None = None
    department: str | None = None
    dense_k: int = 8
    bm25_k: int = 8
    final_k: int = 6

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    conversation_key: str | None = None
    ticket_id: int | None = None

class TicketAssistanceRequest(BaseModel):
    ticket_id: int
    subject: str
    description: str
    category: str = "General"
    priority: str = "Medium"
    asset: dict[str, Any] | None = None

class SourceItem(BaseModel):
    document: str
    page: int | None = None
    section: str | None = None
    chunk_id: int | None = None
    score: float | None = None

class ChatResponse(BaseModel):
    conversation_key: str
    answer: str
    sources: list[SourceItem]
    decomposed_queries: list[str] = []

class TicketAssistanceResponse(BaseModel):
    ticket_id: int
    issue_summary: str
    troubleshooting_steps: list[str]
    sources: list[SourceItem]
    missing_information: list[str]
    escalation_recommended: bool
    escalation_reason: str
