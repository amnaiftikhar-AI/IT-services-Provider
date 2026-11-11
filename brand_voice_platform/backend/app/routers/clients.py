from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Client
from backend.app.schemas import ClientCreate

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("")
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    client = Client(owner_id=user.id, workspace_id=user.workspace_id, name=payload.name, context=payload.context)
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"id": client.id, "name": client.name, "context": client.context}


@router.get("")
def list_clients(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Client).filter(Client.owner_id == user.id, Client.workspace_id == user.workspace_id).all()
    return [{"id": row.id, "name": row.name, "context": row.context} for row in rows]
