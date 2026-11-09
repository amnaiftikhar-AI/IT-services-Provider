from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Ticket, SLAPolicy, Investigation
from app.services.sla_service import calculate_sla
from app.ai.investigator import investigate_ticket

router = APIRouter(prefix="/investigations", tags=["Investigations"])

@router.post("/{ticket_code}")
def investigate(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    policy = db.query(SLAPolicy).filter(
        SLAPolicy.priority == ticket.priority,
        SLAPolicy.active.is_(True)
    ).order_by(SLAPolicy.version.desc()).first()
    if not policy:
        raise HTTPException(status_code=404, detail="No active SLA policy found")
    sla_result = calculate_sla(ticket, policy)
    report = investigate_ticket(db, ticket, ticket.asset, sla_result)
    report["sla"] = sla_result
    record = Investigation(ticket_id=ticket.id, report=report)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"investigation_id": record.id, "ticket_code": ticket_code, "report": report}

@router.get("/{ticket_code}")
def investigation_history(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    rows = db.query(Investigation).filter(
        Investigation.ticket_id == ticket.id
    ).order_by(Investigation.created_at.desc()).all()
    return [{"id": row.id, "created_at": row.created_at, "report": row.report} for row in rows]
