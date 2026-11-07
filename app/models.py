from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base

def now_utc():
    return datetime.now(timezone.utc)

class SupportTeam(Base):
    __tablename__ = "support_teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    department = Column(String(100), nullable=True)
    support_team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    support_team = relationship("SupportTeam")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(String(150), nullable=False)
    asset_type = Column(String(80), nullable=False)
    serial_number = Column(String(120), unique=True, nullable=False)
    assigned_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department = Column(String(100), nullable=True)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="Active")
    assigned_employee = relationship("User")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(30), unique=True, index=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False)
    priority = Column(String(20), nullable=False)
    status = Column(String(30), default="New")
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    support_team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    resolution_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    employee = relationship("User", foreign_keys=[employee_id])
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])
    asset = relationship("Asset")
    support_team = relationship("SupportTeam")

class TicketComment(Base):
    __tablename__ = "ticket_comments"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    user = relationship("User")

class TicketHistory(Base):
    __tablename__ = "ticket_history"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_type = Column(String(50), nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=now_utc)

class SLARule(Base):
    __tablename__ = "sla_rules"
    id = Column(Integer, primary_key=True, index=True)
    priority = Column(String(20), unique=True, nullable=False)
    response_hours = Column(Float, nullable=False)
    resolution_hours = Column(Float, nullable=False)

class SLATracking(Base):
    __tablename__ = "sla_tracking"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), unique=True, nullable=False)
    response_due_at = Column(DateTime(timezone=True), nullable=False)
    resolution_due_at = Column(DateTime(timezone=True), nullable=False)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    total_paused_seconds = Column(Float, default=0)
    ticket = relationship("Ticket")
