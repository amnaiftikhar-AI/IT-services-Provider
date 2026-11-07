from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from amna_rag.database import Base

def now_utc():
    return datetime.now(timezone.utc)

class KBDocument(Base):
    __tablename__ = "kb_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), index=True)
    file_type: Mapped[str] = mapped_column(String(20))
    document_type: Mapped[str] = mapped_column(String(80), default="Technical Guide")
    department: Mapped[str] = mapped_column(String(80), default="IT")
    system_name: Mapped[str] = mapped_column(String(100), default="General IT")
    file_path: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    uploaded_by: Mapped[str] = mapped_column(String(120), default="unknown")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    sections: Mapped[list["KBSection"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["KBChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

class KBSection(Base):
    __tablename__ = "kb_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True)
    section_title: Mapped[str] = mapped_column(String(255), default="General")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    document: Mapped[KBDocument] = relationship(back_populates="sections")
    chunks: Mapped[list["KBChunk"]] = relationship(back_populates="section", cascade="all, delete-orphan")

class KBChunk(Base):
    __tablename__ = "kb_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True)
    parent_section_id: Mapped[int] = mapped_column(ForeignKey("kb_sections.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    parent_section: Mapped[str] = mapped_column(String(255), default="General")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    document: Mapped[KBDocument] = relationship(back_populates="chunks")
    section: Mapped[KBSection] = relationship(back_populates="chunks")
    __table_args__ = (Index("ix_kb_chunks_document_chunk", "document_id", "chunk_index"),)

class AIConversation(Base):
    __tablename__ = "ai_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at")

class AIMessage(Base):
    __tablename__ = "ai_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    conversation: Mapped[AIConversation] = relationship(back_populates="messages")
