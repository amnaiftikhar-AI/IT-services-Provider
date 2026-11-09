import hashlib
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import Document, DocumentChunk
from app.ingestion.loader import load_file
from app.ingestion.chunker import split_pages
from app.ingestion.embedder import embed_texts
from app.retrieval.pinecone_store import upsert_vectors, delete_document_vectors

def ingest_document(db: Session, file_path, document_name, document_type):
    raw = Path(file_path).read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()
    previous = db.query(Document).filter(
        Document.document_name == document_name,
        Document.active.is_(True)
    ).all()
    next_version = max([item.version for item in previous], default=0) + 1
    document = Document(
        document_name=document_name,
        document_type=document_type,
        version=next_version,
        active=True,
        content_hash=content_hash
    )
    db.add(document)
    db.flush()
    chunks = split_pages(load_file(file_path))
    texts = [item["content"] for item in chunks]
    vectors = embed_texts(texts) if texts else []
    records = []
    for item, vector in zip(chunks, vectors):
        code = str(uuid.uuid4())
        row = DocumentChunk(
            chunk_code=code,
            document_id=document.id,
            content=item["content"],
            section=item["section"],
            page_number=item["page_number"],
            chunk_index=item["chunk_index"]
        )
        db.add(row)
        metadata = {
            "document_id": document.id,
            "document_name": document_name,
            "document_type": document_type,
            "version": next_version,
            "section": item["section"],
            "page_number": item["page_number"] or 0,
            "content": item["content"]
        }
        records.append({"id": code, "values": vector, "metadata": metadata})
    db.flush()
    for old in previous:
        old.active = False
        delete_document_vectors(old.id)
    if records:
        upsert_vectors(records)
    db.commit()
    return document
