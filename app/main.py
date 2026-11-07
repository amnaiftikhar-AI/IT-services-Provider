import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from dotenv import load_dotenv

from app.database import Base, engine, get_db
from app.models import User, Ticket, Asset, TicketComment, TicketHistory, SLARule, SLATracking, SupportTeam
from app.schemas import UserCreate, UserOut, TicketCreate, TicketUpdate, AssignTicket, StatusUpdate, ResolveTicket, CommentCreate, AssetCreate, AssetUpdate, SLARuleUpdate
from app.security import hash_password, verify_password, create_access_token, decode_access_token

load_dotenv()
app = FastAPI(title="IT Service Desk - Core Module")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

VALID_ROLES = ["employee", "support_agent", "admin"]
VALID_PRIORITIES = ["Critical", "High", "Medium", "Low"]
VALID_STATUSES = ["New", "Open", "In Progress", "Waiting for User", "Resolved", "Closed"]
ACTIVE_STATUSES = ["Open", "In Progress"]

def utc_now():
    return datetime.now(timezone.utc)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def require_roles(*roles):
    def role_check(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission")
        return current_user
    return role_check

def get_ticket_for_user(ticket_id: int, db: Session, user: User):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if user.role == "employee" and ticket.employee_id != user.id:
        raise HTTPException(status_code=403, detail="You can only access your own tickets")
    if user.role == "support_agent":
        allowed = ticket.assigned_agent_id == user.id
        queue_allowed = ticket.assigned_agent_id is None and ticket.support_team_id == user.support_team_id
        if not (allowed or queue_allowed):
            raise HTTPException(status_code=403, detail="Ticket is outside your permitted queue")
    return ticket

def add_history(db, ticket_id, user_id, change_type, old_value, new_value):
    db.add(TicketHistory(ticket_id=ticket_id, changed_by=user_id, change_type=change_type, old_value=str(old_value) if old_value is not None else None, new_value=str(new_value) if new_value is not None else None))

def get_sla(db, ticket_id):
    return db.query(SLATracking).filter(SLATracking.ticket_id == ticket_id).first()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        teams = ["Hardware", "Network", "Software", "Accounts"]
        for name in teams:
            if not db.query(SupportTeam).filter(SupportTeam.name == name).first():
                db.add(SupportTeam(name=name))

        defaults = [("Critical", 1, 4), ("High", 2, 8), ("Medium", 4, 24), ("Low", 8, 48)]
        for priority, response, resolution in defaults:
            if not db.query(SLARule).filter(SLARule.priority == priority).first():
                db.add(SLARule(priority=priority, response_hours=response, resolution_hours=resolution))

        admin_email = os.getenv("ADMIN_EMAIL", "admin@servicedesk.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
        admin_name = os.getenv("ADMIN_NAME", "Service Desk Admin")

        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name=admin_name,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
                is_active=True
            )
            db.add(admin)

        db.commit()
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "IT Service Desk API is running"}

@app.post("/auth/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.role not in ["employee", "support_agent"]:
        raise HTTPException(status_code=400, detail="Public registration is only available for employees and support agents. Admin is created through the seed.")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if data.role == "support_agent" and data.support_team_id:
        team = db.query(SupportTeam).filter(SupportTeam.id == data.support_team_id).first()
        if not team:
            raise HTTPException(status_code=400, detail="Support team not found")
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role=data.role, department=data.department, support_team_id=data.support_team_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    return db.query(User).all()

@app.get("/users/managers", response_model=list[UserOut])
def list_agents(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "support_agent"))):
    return db.query(User).filter(User.role == "support_agent", User.is_active == True).all()

@app.get("/support-teams")
def list_teams(db: Session = Depends(get_db)):
    return db.query(SupportTeam).all()

@app.post("/tickets")
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), employee: User = Depends(require_roles("employee"))):
    if data.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")
    if data.asset_id:
        asset = db.query(Asset).filter(Asset.id == data.asset_id, Asset.status == "Active").first()
        if not asset or asset.assigned_employee_id != employee.id:
            raise HTTPException(status_code=400, detail="Asset is not assigned to you or is inactive")
    team_id = data.support_team_id
    if team_id is None:
        team_name = data.category if data.category in ["Hardware", "Network", "Software", "Accounts"] else None
        team = db.query(SupportTeam).filter(SupportTeam.name == team_name).first() if team_name else None
        team_id = int(team.id) if team else None
    ticket = Ticket(ticket_number="TEMP", employee_id=employee.id, subject=data.subject, description=data.description, category=data.category, priority=data.priority, status="New", asset_id=data.asset_id, support_team_id=team_id)
    db.add(ticket)
    db.flush()
    setattr(ticket, "ticket_number", f"TKT-{ticket.id:05d}")
    rule = db.query(SLARule).filter(SLARule.priority == data.priority).first()
    if rule is None:
        raise HTTPException(status_code=500, detail="No SLA rule configured for this priority")
    now = utc_now()
    db.add(SLATracking(ticket_id=ticket.id, response_due_at=now + timedelta(hours=float(rule.response_hours)), resolution_due_at=now + timedelta(hours=float(rule.resolution_hours))))
    add_history(db, ticket.id, employee.id, "status", None, "New")
    db.commit()
    db.refresh(ticket)
    return {"message": "Ticket created", "ticket_id": ticket.id, "ticket_number": ticket.ticket_number}

@app.get("/tickets")
def list_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Ticket)
    if current_user.role == "employee":
        query = query.filter(Ticket.employee_id == current_user.id)
    elif current_user.role == "support_agent":
        query = query.filter(or_(Ticket.assigned_agent_id == current_user.id, (Ticket.assigned_agent_id.is_(None) & (Ticket.support_team_id == current_user.support_team_id))))
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return [ticket_data(t, db) for t in tickets]

def ticket_data(ticket, db):
    sla = get_sla(db, ticket.id)
    now = utc_now()
    sla_clock = sla.paused_at if sla and sla.paused_at else now
    response_remaining = max(0, int((sla.response_due_at - sla_clock).total_seconds())) if sla and sla.first_response_at is None else None
    resolution_remaining = max(0, int((sla.resolution_due_at - sla_clock).total_seconds())) if sla and sla.resolved_at is None else None
    response_overdue = max(0, int((sla_clock - sla.response_due_at).total_seconds())) if sla and sla.first_response_at is None else 0
    resolution_overdue = max(0, int((sla_clock - sla.resolution_due_at).total_seconds())) if sla and sla.resolved_at is None else 0
    response_breached = bool(response_overdue > 0 and not (sla and sla.paused_at))
    resolution_breached = bool(resolution_overdue > 0 and not (sla and sla.paused_at))
    return {
        "id": ticket.id, "ticket_number": ticket.ticket_number, "employee_id": ticket.employee_id,
        "employee_name": ticket.employee.name if ticket.employee else None,
        "subject": ticket.subject, "description": ticket.description, "category": ticket.category,
        "priority": ticket.priority, "status": ticket.status, "assigned_agent_id": ticket.assigned_agent_id,
        "assigned_agent_name": ticket.assigned_agent.name if ticket.assigned_agent else None,
        "support_team_id": ticket.support_team_id, "asset_id": ticket.asset_id,
        "asset_name": ticket.asset.asset_name if ticket.asset else None,
        "resolution_details": ticket.resolution_details,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "response_due_at": sla.response_due_at.isoformat() if sla else None,
        "resolution_due_at": sla.resolution_due_at.isoformat() if sla else None,
        "sla_paused": bool(sla and sla.paused_at),
        "response_breached": response_breached, "resolution_breached": resolution_breached,
        "response_remaining_seconds": response_remaining, "resolution_remaining_seconds": resolution_remaining,
        "response_overdue_seconds": response_overdue, "resolution_overdue_seconds": resolution_overdue
    }

@app.get("/tickets/{ticket_id}")
def ticket_details(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = get_ticket_for_user(ticket_id, db, current_user)
    return ticket_data(ticket, db)

@app.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db), agent: User = Depends(require_roles("support_agent", "admin"))):
    ticket = get_ticket_for_user(ticket_id, db, agent)
    changes = data.model_dump(exclude_unset=True)
    old_priority = ticket.priority
    for field, value in changes.items():
        if field == "priority" and value not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        if field == "status" and value not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        old = getattr(ticket, field)
        setattr(ticket, field, value)
        add_history(db, ticket.id, agent.id, field, old, value)
    if "priority" in changes and ticket.priority != old_priority:
        rule = db.query(SLARule).filter(SLARule.priority == ticket.priority).first()
        sla = get_sla(db, ticket.id)
        if rule and sla:
            pause_seconds = float(sla.total_paused_seconds or 0)
            response_hours = float(rule.response_hours)
            resolution_hours = float(rule.resolution_hours)
            sla.response_due_at = ticket.created_at + timedelta(hours=response_hours, seconds=pause_seconds)
            sla.resolution_due_at = ticket.created_at + timedelta(hours=resolution_hours, seconds=pause_seconds)
    ticket.updated_at = utc_now()
    db.commit()
    return {"message": "Ticket updated"}

@app.patch("/tickets/{ticket_id}/assign")
def assign_ticket(ticket_id: int, data: AssignTicket, db: Session = Depends(get_db), agent: User = Depends(require_roles("support_agent", "admin"))):
    ticket = get_ticket_for_user(ticket_id, db, agent)
    if data.assigned_agent_id is not None:
        target = db.query(User).filter(User.id == data.assigned_agent_id, User.role == "support_agent", User.is_active == True).first()
        if not target:
            raise HTTPException(status_code=400, detail="Target support agent not found")
        if agent.role == "support_agent" and target.support_team_id != agent.support_team_id:
            raise HTTPException(status_code=403, detail="Cannot assign outside your support team")
        ticket.support_team_id = target.support_team_id
    old = ticket.assigned_agent_id
    ticket.assigned_agent_id = data.assigned_agent_id
    add_history(db, ticket.id, agent.id, "assignment", old, ticket.assigned_agent_id)
    db.commit()
    return {"message": "Ticket assignment updated"}

@app.patch("/tickets/{ticket_id}/status")
def change_status(ticket_id: int, data: StatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = get_ticket_for_user(ticket_id, db, current_user)
    if current_user.role not in ["support_agent", "admin"]:
        raise HTTPException(status_code=403, detail="Only support staff can change ticket status here")
    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    sla = get_sla(db, ticket.id)
    old = ticket.status
    now = utc_now()
    if data.status == "Waiting for User" and old != "Waiting for User" and sla and not sla.paused_at:
        sla.paused_at = now
    if old == "Waiting for User" and data.status != "Waiting for User" and sla and sla.paused_at:
        paused_duration = now - sla.paused_at
        sla.total_paused_seconds += paused_duration.total_seconds()
        sla.response_due_at = sla.response_due_at + paused_duration
        sla.resolution_due_at = sla.resolution_due_at + paused_duration
        sla.paused_at = None
    ticket.status = data.status
    ticket.updated_at = now
    add_history(db, ticket.id, current_user.id, "status", old, data.status)
    db.commit()
    return {"message": "Status updated", "sla_paused": bool(sla and sla.paused_at)}

@app.patch("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, data: ResolveTicket, db: Session = Depends(get_db), agent: User = Depends(require_roles("support_agent", "admin"))):
    ticket = get_ticket_for_user(ticket_id, db, agent)
    old = ticket.status
    ticket.status = "Resolved"
    ticket.resolution_details = data.resolution_details
    ticket.updated_at = utc_now()
    sla = get_sla(db, ticket.id)
    if sla:
        sla.resolved_at = utc_now()
        if sla.paused_at:
            paused_duration = sla.resolved_at - sla.paused_at
            sla.total_paused_seconds += paused_duration.total_seconds()
            sla.response_due_at += paused_duration
            sla.resolution_due_at += paused_duration
            sla.paused_at = None
    add_history(db, ticket.id, agent.id, "status", old, "Resolved")
    db.commit()
    return {"message": "Ticket resolved"}

@app.patch("/tickets/{ticket_id}/confirm")
def confirm_resolution(ticket_id: int, db: Session = Depends(get_db), employee: User = Depends(require_roles("employee"))):
    ticket = get_ticket_for_user(ticket_id, db, employee)
    if ticket.status != "Resolved":
        raise HTTPException(status_code=400, detail="Only resolved tickets can be confirmed")
    old = ticket.status
    ticket.status = "Closed"
    add_history(db, ticket.id, employee.id, "status", old, "Closed")
    db.commit()
    return {"message": "Resolution confirmed and ticket closed"}

@app.patch("/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db), employee: User = Depends(require_roles("employee"))):
    ticket = get_ticket_for_user(ticket_id, db, employee)
    if ticket.status != "Resolved":
        raise HTTPException(status_code=400, detail="Only resolved tickets can be reopened")
    old = ticket.status
    ticket.status = "Open"
    ticket.updated_at = utc_now()
    add_history(db, ticket.id, employee.id, "status", old, "Open")
    db.commit()
    return {"message": "Ticket reopened"}

@app.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: int, data: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = get_ticket_for_user(ticket_id, db, current_user)
    if data.is_internal and current_user.role not in ["support_agent", "admin"]:
        raise HTTPException(status_code=403, detail="Only support staff can add internal notes")
    comment = TicketComment(ticket_id=ticket.id, user_id=current_user.id, content=data.content, is_internal=data.is_internal)
    db.add(comment)
    if current_user.role in ["support_agent", "admin"]:
        sla = get_sla(db, ticket.id)
        if sla and not sla.first_response_at and not data.is_internal:
            sla.first_response_at = utc_now()
    db.commit()
    return {"message": "Comment added"}

@app.get("/tickets/{ticket_id}/comments")
def get_comments(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = get_ticket_for_user(ticket_id, db, current_user)
    query = db.query(TicketComment).filter(TicketComment.ticket_id == ticket.id)
    if current_user.role == "employee":
        query = query.filter(TicketComment.is_internal == False)
    comments = query.order_by(TicketComment.created_at).all()
    return [{"id": c.id, "user_id": c.user_id, "user_name": c.user.name, "content": c.content, "is_internal": c.is_internal, "created_at": c.created_at.isoformat()} for c in comments]

@app.get("/tickets/{ticket_id}/history")
def get_history(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = get_ticket_for_user(ticket_id, db, current_user)
    rows = db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket.id).order_by(TicketHistory.changed_at).all()
    return [{"change_type": r.change_type, "old_value": r.old_value, "new_value": r.new_value, "changed_by": r.changed_by, "changed_at": r.changed_at.isoformat()} for r in rows]

@app.post("/assets")
def create_asset(data: AssetCreate, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if db.query(Asset).filter(Asset.serial_number == data.serial_number).first():
        raise HTTPException(status_code=400, detail="Serial number already exists")
    if data.assigned_employee_id:
        employee = db.query(User).filter(User.id == data.assigned_employee_id, User.role == "employee").first()
        if not employee:
            raise HTTPException(status_code=400, detail="Employee not found")
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"message": "Asset created", "asset_id": asset.id}

@app.get("/assets")
def list_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Asset)
    if current_user.role == "employee":
        query = query.filter(Asset.assigned_employee_id == current_user.id)
    assets = query.all()
    return [{"id": a.id, "asset_name": a.asset_name, "asset_type": a.asset_type, "serial_number": a.serial_number, "assigned_employee_id": a.assigned_employee_id, "department": a.department, "status": a.status} for a in assets]

@app.get("/assets/{asset_id}")
def asset_details(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if current_user.role == "employee" and asset.assigned_employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot access this asset")
    return {"id": asset.id, "asset_name": asset.asset_name, "asset_type": asset.asset_type, "serial_number": asset.serial_number, "assigned_employee_id": asset.assigned_employee_id, "department": asset.department, "status": asset.status}

@app.patch("/assets/{asset_id}")
def update_asset(asset_id: int, data: AssetUpdate, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)
    db.commit()
    return {"message": "Asset updated"}

@app.patch("/assets/{asset_id}/deactivate")
def deactivate_asset(asset_id: int, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    setattr(asset, "status", "Inactive")
    db.commit()
    return {"message": "Asset deactivated"}

@app.get("/sla/rules")
def get_sla_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [{"priority": r.priority, "response_hours": r.response_hours, "resolution_hours": r.resolution_hours} for r in db.query(SLARule).all()]

@app.put("/sla/rules/{priority}")
def update_sla_rule(priority: str, data: SLARuleUpdate, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")
    rule = db.query(SLARule).filter(SLARule.priority == priority).first()
    if not rule:
        rule = SLARule(priority=priority, response_hours=data.response_hours, resolution_hours=data.resolution_hours)
        db.add(rule)
    else:
        setattr(rule, "response_hours", float(data.response_hours))
        setattr(rule, "resolution_hours", float(data.resolution_hours))
    db.commit()
    return {"message": "SLA rule updated"}

@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    tickets = db.query(Ticket).all()
    status_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for ticket in tickets:
        status = str(ticket.status)
        status_counts[status] = status_counts.get(status, 0) + 1
        priority = str(ticket.priority)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    breached = 0
    for ticket in tickets:
        sla = get_sla(db, ticket.id)
        if sla and sla.paused_at is None:
            if (sla.first_response_at is None and utc_now() > sla.response_due_at) or (sla.resolved_at is None and utc_now() > sla.resolution_due_at):
                breached += 1
    return {"total_tickets": len(tickets), "status_distribution": status_counts, "priority_distribution": priority_counts, "sla_breaches": breached}

@app.post("/tickets/{ticket_id}/ai-assistance")
def prepare_ai_assistance(ticket_id: int, db: Session = Depends(get_db), agent: User = Depends(require_roles("support_agent", "admin"))):
    ticket = get_ticket_for_user(ticket_id, db, agent)
    payload = {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "asset": {
            "asset_id": ticket.asset.id,
            "asset_name": ticket.asset.asset_name,
            "asset_type": ticket.asset.asset_type,
            "serial_number": ticket.asset.serial_number
        } if ticket.asset else None
    }
    ai_url = os.getenv("AI_ASSISTANT_URL")
    if ai_url:
        import requests
        response = requests.post(ai_url, json=payload, timeout=60)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="AI service returned an error")
        return response.json()
    return {"message": "AI endpoint is not configured. This is the ticket payload prepared for Amna's API.", "request_payload": payload}
