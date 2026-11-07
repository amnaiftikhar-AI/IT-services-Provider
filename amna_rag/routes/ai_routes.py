from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from amna_rag.database import get_db
from amna_rag.dependencies import get_current_user, require_roles
from amna_rag.models import AIConversation, AIMessage
from amna_rag.schemas import ChatRequest, TicketAssistanceRequest
from amna_rag.services.assistant_service import ask_question, conversation_history, ticket_assistance

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.ticket_id is not None and user.role not in {"admin", "support_agent"}: raise HTTPException(403, "Only support staff can start a ticket investigation")
    try: return ask_question(db, user.id, payload.question, payload.conversation_key, payload.ticket_id)
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user=Depends(get_current_user)):
    conversations = conversation_history(db, user.id, user.role)
    return [{"conversation_key": c.conversation_key, "ticket_id": c.ticket_id, "title": c.title, "updated_at": c.updated_at, "messages": [{"role": m.role, "content": m.content, "sources": m.sources_json} for m in c.messages]} for c in conversations]

@router.post("/ticket-assistance")
def assist_ticket(payload: TicketAssistanceRequest, db: Session = Depends(get_db), user=Depends(require_roles("admin", "support_agent"))):
    try: return ticket_assistance(db, user.id, payload)
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@router.delete("/conversations/{conversation_key}")
def delete_conversation(conversation_key: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    conversation = db.query(AIConversation).filter_by(conversation_key=conversation_key).first()
    if not conversation: raise HTTPException(404, "Conversation not found")
    if conversation.user_id != user.id and user.role != "admin": raise HTTPException(403, "You cannot delete this conversation")
    db.delete(conversation); db.commit()
    return {"message": "Conversation and its messages deleted"}
