from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from backend.app.models import DocumentChunk, Preference
from backend.app.services.embeddings import embed_query


def retrieve_context(db: Session, user, client_id: int | None, query: str, limit: int = 15):
    vector = embed_query(query)
    allowed_scope = or_(
        and_(DocumentChunk.owner_id == user.id, DocumentChunk.workspace_id == user.workspace_id),
        and_(DocumentChunk.owner_id == 0, DocumentChunk.company_id == user.company_id),
    )
    client_scope = or_(DocumentChunk.client_id.is_(None), DocumentChunk.client_id == client_id) if client_id else DocumentChunk.client_id.is_(None)
    rows = (
        db.query(DocumentChunk)
        .filter(
            allowed_scope,
            client_scope,
            DocumentChunk.is_active.is_(True),
            DocumentChunk.approval_status != "rejected",
        )
        .order_by(DocumentChunk.embedding.cosine_distance(vector))
        .limit(limit)
        .all()
    )
    preferences = (
        db.query(Preference)
        .filter(
            Preference.owner_id == user.id,
            Preference.status == "active",
            or_(Preference.client_id.is_(None), Preference.client_id == client_id),
        )
        .order_by(Preference.updated_at.desc())
        .limit(20)
        .all()
    )
    approved = [row for row in rows if row.approval_status == "approved"]
    other = [row for row in rows if row.approval_status != "approved"]
    ranked = approved + other
    return ranked[:8], preferences
