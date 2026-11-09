from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Ticket, SLAPolicy, RiskSnapshot
from app.services.sla_service import calculate_sla

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/risks")
def risk_dashboard(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).filter(Ticket.status.notin_(["Resolved", "Closed"])).all()
    output = []
    for ticket in tickets:
        policy = db.query(SLAPolicy).filter(
            SLAPolicy.priority == ticket.priority,
            SLAPolicy.active.is_(True)
        ).order_by(SLAPolicy.version.desc()).first()
        if not policy:
            continue
        result = calculate_sla(ticket, policy)
        output.append({
            "ticket_code": ticket.ticket_code,
            "subject": ticket.subject,
            "priority": ticket.priority,
            "risk_level": result["risk_level"],
            "resolution_remaining_minutes": result["resolution_remaining_minutes"]
        })
    return output
