from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Ticket, Asset, SLAPolicy
from app.schemas import TicketCreate, TicketOut
from app.services.sla_service import calculate_sla

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.get("/", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()

@router.post("/", response_model=TicketOut)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    asset = None
    if payload.asset_code:
        asset = db.query(Asset).filter(Asset.asset_code == payload.asset_code).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
    ticket = Ticket(
        ticket_code=payload.ticket_code,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        category=payload.category,
        asset_id=asset.id if asset else None,
        status=payload.status,
        created_at=payload.created_at
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

@router.get("/{ticket_code}", response_model=TicketOut)
def get_ticket(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.get("/{ticket_code}/sla")
def get_ticket_sla(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    policy = db.query(SLAPolicy).filter(
        SLAPolicy.priority == ticket.priority,
        SLAPolicy.active.is_(True)
    ).order_by(SLAPolicy.version.desc()).first()
    if not policy:
        raise HTTPException(status_code=404, detail="No active SLA policy for ticket priority")
    return calculate_sla(ticket, policy)
