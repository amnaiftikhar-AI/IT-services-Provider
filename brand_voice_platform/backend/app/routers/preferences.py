from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Preference
from backend.app.schemas import PreferenceUpdate

router = APIRouter(prefix="/preferences", tags=["Preferences"])


@router.get("")
def list_preferences(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Preference).filter(Preference.owner_id == user.id).order_by(Preference.updated_at.desc()).all()
    return [
        {
            "id": p.id,
            "client_id": p.client_id,
            "type": p.preference_type,
            "value": p.preference_value,
            "confidence": p.confidence,
            "evidence_count": p.evidence_count,
            "status": p.status,
        }
        for p in rows
    ]


@router.patch("/{preference_id}")
def update_preference(preference_id: int, payload: PreferenceUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(Preference).filter(Preference.id == preference_id, Preference.owner_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Preference not found")
    row.status = payload.status
    db.commit()
    return {"id": row.id, "status": row.status}


@router.delete("/{preference_id}")
def delete_preference(preference_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(Preference).filter(Preference.id == preference_id, Preference.owner_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Preference not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}
