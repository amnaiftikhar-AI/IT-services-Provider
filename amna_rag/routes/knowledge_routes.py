from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from amna_rag.database import get_db
from amna_rag.dependencies import get_current_user, require_roles
from amna_rag.models import KBDocument
from amna_rag.schemas import SearchRequest
from amna_rag.services.ingestion_service import ingest_file, rebuild_all, delete_document
from amna_rag.services.retrieval_service import hybrid_search
from amna_rag.config import settings

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...), document_type: str = Form("Technical Guide"), department: str = Form("IT"), system_name: str = Form("General IT"), db: Session = Depends(get_db), user=Depends(require_roles("admin", "support_agent"))):
    results = []
    for file in files:
        content = await file.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"{file.filename} exceeds upload limit")
        try:
            doc, count = ingest_file(db, file.filename or "upload.txt", content, user.id, document_type, department, system_name)
            results.append({"id": doc.id, "filename": doc.filename, "chunks": count, "status": "indexed"})
        except ValueError as exc: results.append({"filename": file.filename, "status": "skipped", "message": str(exc)})
        except Exception as exc:
            db.rollback(); raise HTTPException(400, f"Could not process {file.filename}: {exc}")
    return {"uploaded": results}

@router.get("/documents")
def list_documents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    docs = db.query(KBDocument).order_by(KBDocument.uploaded_at.desc()).all()
    return [{"id": d.id, "filename": d.filename, "file_type": d.file_type, "document_type": d.document_type, "department": d.department, "system_name": d.system_name, "uploaded_by": d.uploaded_by, "uploaded_at": d.uploaded_at, "is_indexed": d.is_indexed, "chunk_count": len(d.chunks)} for d in docs]

@router.put("/documents/{document_id}")
async def update_document(document_id: int, file: UploadFile = File(...), document_type: str = Form("Technical Guide"), department: str = Form("IT"), system_name: str = Form("General IT"), db: Session = Depends(get_db), user=Depends(require_roles("admin", "support_agent"))):
    old_doc = db.query(KBDocument).filter_by(id=document_id).first()
    if not old_doc: raise HTTPException(404, "Document not found")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "File exceeds upload limit")
    from hashlib import sha256
    new_hash = sha256(content).hexdigest()
    if new_hash == old_doc.content_hash:
        return {"message": "The uploaded file is unchanged", "id": old_doc.id}
    duplicate = db.query(KBDocument).filter(KBDocument.content_hash == new_hash, KBDocument.id != document_id).first()
    if duplicate: raise HTTPException(409, f"This file already exists as {duplicate.filename}")
    old_path = old_doc.file_path
    db.delete(old_doc); db.commit()
    from pathlib import Path
    Path(old_path).unlink(missing_ok=True)
    try:
        new_doc, count = ingest_file(db, file.filename or old_doc.filename, content, user.id, document_type, department, system_name)
        rebuild_all(db)
        return {"message": "Document updated and re-indexed", "id": new_doc.id, "filename": new_doc.filename, "chunks": count}
    except Exception as exc:
        db.rollback()
        rebuild_all(db)
        raise HTTPException(400, f"Could not update document: {exc}")

@router.delete("/documents/{document_id}")
def remove_document(document_id: int, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    doc = db.query(KBDocument).filter_by(id=document_id).first()
    if not doc: raise HTTPException(404, "Document not found")
    delete_document(db, doc)
    return {"message": "Document deleted and FAISS index rebuilt"}

@router.post("/reindex")
def reindex(db: Session = Depends(get_db), user=Depends(require_roles("admin", "support_agent"))):
    return {"chunks_indexed": rebuild_all(db), "message": "FAISS index rebuilt from PostgreSQL chunks"}

@router.post("/search")
def search(payload: SearchRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    results = hybrid_search(db, payload.question, payload.dense_k, payload.bm25_k, payload.final_k, payload.document_type, payload.department)
    return [{"content": x["content"], "metadata": x["metadata"], "rrf_score": x["rrf"]} for x in results]
