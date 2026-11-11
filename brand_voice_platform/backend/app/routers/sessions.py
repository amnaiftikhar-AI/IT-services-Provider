from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Client, WritingSession, Message
from backend.app.schemas import SessionCreate, SessionUpdate
from backend.app.services.redis_memory import get_recent_messages, save_recent_messages, clear_session_memory

router = APIRouter(prefix="/sessions", tags=["Writing Sessions"])


def owned_session(db, user, session_id):
    return db.query(WritingSession).filter(
        WritingSession.id == session_id,
        WritingSession.owner_id == user.id,
        WritingSession.workspace_id == user.workspace_id,
    ).first()


@router.post("")
def create_session(payload: SessionCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.client_id is not None:
        client = db.query(Client).filter(Client.id == payload.client_id, Client.owner_id == user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    row = WritingSession(owner_id=user.id, workspace_id=user.workspace_id, client_id=payload.client_id, title=payload.title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "title": row.title, "client_id": row.client_id, "status": row.status}


@router.get("")
def list_sessions(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(WritingSession).filter(WritingSession.owner_id == user.id).order_by(WritingSession.updated_at.desc()).all()
    return [{"id": r.id, "title": r.title, "client_id": r.client_id, "status": r.status} for r in rows]


@router.patch("/{session_id}")
def rename_session(session_id: int, payload: SessionUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = owned_session(db, user, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.title:
        row.title = payload.title
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": row.id, "title": row.title}


@router.post("/{session_id}/close")
def close_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = owned_session(db, user, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    row.status = "closed"
    db.commit()
    clear_session_memory(user.id, session_id)
    return {"status": "closed"}


@router.post("/{session_id}/resume")
def resume_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = owned_session(db, user, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    row.status = "active"
    messages = db.query(Message).filter(Message.session_id == session_id, Message.owner_id == user.id).order_by(Message.id.desc()).limit(12).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(messages)]
    save_recent_messages(user.id, session_id, history)
    db.commit()
    return {"status": "active", "messages_restored": len(history), "client_id": row.client_id}
