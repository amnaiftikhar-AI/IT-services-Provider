from pathlib import PurePosixPath
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pypdf import PdfReader
from io import BytesIO
from backend.app.core.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Client, Document, DocumentChunk
from backend.app.services.storage import upload_document
from backend.app.services.chunking import split_document
from backend.app.services.embeddings import embed_texts

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED = {"pdf", "txt"}
CATEGORIES = {
    "brand_guideline", "proposal_template", "previous_email",
    "approved_example", "rejected_example", "client_brief",
    "company_guideline", "other"
}


def extract_text(filename: str, content: bytes) -> str:
    suffix = PurePosixPath(filename).suffix.lower().lstrip(".")
    if suffix == "txt":
        return content.decode("utf-8", errors="replace")
    reader = PdfReader(BytesIO(content))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    category: str = Form(...),
    client_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    suffix = PurePosixPath(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid document category")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds upload size limit")
    client = None
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.owner_id == user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    text = extract_text(file.filename or "upload", content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in document")
    safe_name = (file.filename or "document").replace("/", "_").replace("\\", "_")
    path = f"users/{user.id}/workspace/{user.workspace_id}/{safe_name}"
    try:
        upload_document(path, content, file.content_type or "application/octet-stream")
        chunks = split_document(text)
        vectors = embed_texts(chunks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Document processing failed: {exc}")
    doc = Document(
        owner_id=user.id,
        workspace_id=user.workspace_id,
        client_id=client.id if client else None,
        category=category,
        filename=safe_name,
        storage_path=path,
    )
    db.add(doc)
    db.flush()
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.add(DocumentChunk(
            document_id=doc.id,
            owner_id=user.id,
            workspace_id=user.workspace_id,
            company_id=user.company_id,
            client_id=client.id if client else None,
            category=category,
            approval_status="approved" if category == "approved_example" else "rejected" if category == "rejected_example" else "unreviewed",
            content=chunk,
            chunk_index=index,
            embedding=vector,
        ))
    db.commit()
    return {"document_id": doc.id, "filename": doc.filename, "chunks_created": len(chunks), "storage_path": path}


@router.get("")
def list_documents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Document).filter(Document.owner_id == user.id, Document.workspace_id == user.workspace_id).all()
    return [
        {"id": row.id, "filename": row.filename, "category": row.category, "client_id": row.client_id, "is_active": row.is_active}
        for row in rows
    ]
