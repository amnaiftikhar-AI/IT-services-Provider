import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, SLAPolicy
from app.schemas import ChatRequest
from app.memory.chat_memory import get_history, save_message
from app.services.sla_service import calculate_sla
from app.retrieval.hybrid_retriever import hybrid_search
from app.ai.llm import ask_llm
from app.ai.prompts import FOLLOWUP_SYSTEM_PROMPT

router = APIRouter(prefix="/chat", tags=["Ticket Chat"])


@router.post("/{ticket_code}")
def chat(ticket_code: str, payload: ChatRequest, db: Session = Depends(get_db)):

    ticket = db.query(Ticket).filter(
        Ticket.ticket_code == ticket_code
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    policy = db.query(SLAPolicy).filter(
        SLAPolicy.priority == ticket.priority,
        SLAPolicy.active.is_(True)
    ).order_by(SLAPolicy.version.desc()).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="No active SLA policy found"
        )

    sla = calculate_sla(ticket, policy)

    history = get_history(db, ticket.id)

    evidence = hybrid_search(
        db,
        payload.question,
        top_k=6
    )

    context = {
        "current_ticket": {
            "ticket_code": ticket.ticket_code,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "category": ticket.category
        },
        "asset": None if not ticket.asset else {
            "asset_code": ticket.asset.asset_code,
            "environment": ticket.asset.environment,
            "criticality": ticket.asset.criticality
        },
        "sla_calculated_by_python": sla,
        "retrieved_evidence": evidence,
        "conversation_history_for_current_ticket_only": history,
        "question": payload.question
    }

    answer = ask_llm(
        FOLLOWUP_SYSTEM_PROMPT,
        json.dumps(context, default=str)
    )

    save_message(db, ticket.id, "user", payload.question)
    save_message(db, ticket.id, "assistant", answer)

    return {
        "ticket_code": ticket_code,
        "answer": answer
    }


@router.get("/{ticket_code}/history")
def history(ticket_code: str, db: Session = Depends(get_db)):

    ticket = db.query(Ticket).filter(
        Ticket.ticket_code == ticket_code
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    rows = get_history(db, ticket.id, limit=500)

    return {
        "ticket_code": ticket_code,
        "messages": rows
    }