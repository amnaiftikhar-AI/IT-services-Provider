from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Client, WritingSession, Draft, Message
from backend.app.schemas import GenerateRequest, FeedbackRequest, RevisionRequest
from backend.app.services.redis_memory import get_recent_messages, save_recent_messages
from backend.app.services.rag import build_draft

router = APIRouter(prefix="/drafts", tags=["Drafts"])


def verify_session(db, user, session_id):
    return db.query(WritingSession).filter(
        WritingSession.id == session_id,
        WritingSession.owner_id == user.id,
        WritingSession.workspace_id == user.workspace_id,
        WritingSession.status == "active",
    ).first()


@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = verify_session(db, user, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")
    client_id = payload.client_id if payload.client_id is not None else session.client_id
    client = None
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.owner_id == user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    history = get_recent_messages(user.id, session.id)
    try:
        draft_text, retrieved = build_draft(db, user, client, session, payload.task, history)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}")
    draft = Draft(
        owner_id=user.id,
        workspace_id=user.workspace_id,
        client_id=client.id if client else None,
        session_id=session.id,
        task=payload.task,
        original_text=draft_text,
    )
    db.add(draft)
    db.add(Message(session_id=session.id, owner_id=user.id, role="user", content=payload.task))
    db.add(Message(session_id=session.id, owner_id=user.id, role="assistant", content=draft_text))
    db.commit()
    db.refresh(draft)
    updated = history + [{"role": "user", "content": payload.task}, {"role": "assistant", "content": draft_text}]
    save_recent_messages(user.id, session.id, updated)
    session.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    db.commit()
    return {
        "draft_id": draft.id,
        "draft": draft_text,
        "retrieved_chunks": len(retrieved),
        "client_id": client.id if client else None,
    }


@router.post("/{draft_id}/feedback")
def feedback(draft_id: int, payload: FeedbackRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.owner_id == user.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if payload.action not in {"approved", "rejected", "needs_revision"}:
        raise HTTPException(status_code=400, detail="Invalid feedback action")
    draft.status = payload.action
    draft.rating = payload.rating
    db.commit()
    return {"draft_id": draft.id, "status": draft.status, "rating": draft.rating}


@router.post("/{draft_id}/revise")
def revise(draft_id: int, payload: RevisionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.owner_id == user.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.final_text = payload.final_text
    db.commit()
    from backend.app.services.llm import extract_preferences
    from backend.app.models import Preference, PreferenceEvidence
    candidates = []
    try:
        candidates = extract_preferences(draft.original_text, payload.final_text)
    except Exception:
        candidates = []
    saved = []
    for item in candidates[:3]:
        if not isinstance(item, dict):
            continue
        pref_type = str(item.get("preference_type", "style"))[:80]
        pref_value = str(item.get("preference_value", ""))[:500]
        if not pref_value:
            continue
        pref = Preference(
            owner_id=user.id,
            workspace_id=user.workspace_id,
            client_id=draft.client_id,
            preference_type=pref_type,
            preference_value=pref_value,
            confidence=max(0.0, min(1.0, float(item.get("confidence", 0.5)))),
            evidence_count=1,
            status="candidate",
            source="edit",
        )
        db.add(pref)
        db.flush()
        db.add(PreferenceEvidence(
            preference_id=pref.id,
            owner_id=user.id,
            draft_id=draft.id,
            evidence=str(item.get("evidence", "User revised generated text"))[:3000],
        ))
        saved.append(pref.id)
    db.commit()
    return {"draft_id": draft.id, "candidate_preferences_created": saved}


@router.get("/{draft_id}")
def get_draft(draft_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.owner_id == user.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {
        "id": draft.id,
        "task": draft.task,
        "original_text": draft.original_text,
        "final_text": draft.final_text,
        "status": draft.status,
        "rating": draft.rating,
    }
