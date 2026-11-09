import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document
from app.services.document_service import ingest_document

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("general"),
    db: Session = Depends(get_db)
):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(content)
        temp_path = temp.name
    try:
        document = ingest_document(db, temp_path, file.filename, document_type)
        return {
            "id": document.id,
            "document_name": document.document_name,
            "version": document.version,
            "active": document.active
        }
    finally:
        os.unlink(temp_path)

@router.get("/")
def list_documents(db: Session = Depends(get_db)):
    rows = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": row.id,
            "document_name": row.document_name,
            "document_type": row.document_type,
            "version": row.version,
            "active": row.active,
            "uploaded_at": row.uploaded_at
        } for row in rows
    ]
