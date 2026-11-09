from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    asset_code = Column(String(100), unique=True, nullable=False, index=True)
    asset_type = Column(String(100), nullable=False)
    environment = Column(String(50), nullable=False)
    criticality = Column(String(50), nullable=False)
    description = Column(Text, default="")

class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    priority = Column(String(30), nullable=False, index=True)
    response_minutes = Column(Integer, nullable=False)
    resolution_minutes = Column(Integer, nullable=False)
    business_hours_only = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    effective_from = Column(DateTime(timezone=True), server_default=func.now())
    effective_to = Column(DateTime(timezone=True), nullable=True)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    ticket_code = Column(String(100), unique=True, nullable=False, index=True)
    subject = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(30), nullable=False)
    category = Column(String(100), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    status = Column(String(50), default="Open")
    assigned_to = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    paused_minutes = Column(Integer, default=0)
    asset = relationship("Asset")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    document_name = Column(String(300), nullable=False)
    document_type = Column(String(50), nullable=False)
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    content_hash = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    chunk_code = Column(String(150), unique=True, nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    section = Column(String(300), default="")
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    document = relationship("Document", back_populates="chunks")

class HistoricalIncident(Base):
    __tablename__ = "historical_incidents"
    id = Column(Integer, primary_key=True)
    incident_code = Column(String(100), unique=True, nullable=False, index=True)
    subject = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    asset_code = Column(String(100), nullable=True)
    error_code = Column(String(100), nullable=True, index=True)
    root_cause = Column(Text, nullable=False)
    resolution_steps = Column(Text, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    report = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ticket = relationship("Ticket")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    risk_level = Column(String(30), nullable=False)
    response_remaining_minutes = Column(Float, nullable=True)
    resolution_remaining_minutes = Column(Float, nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("ticket_id", "checked_at"),)
