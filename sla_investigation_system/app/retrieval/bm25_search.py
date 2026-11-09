import re
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from app.models import DocumentChunk, Document, HistoricalIncident

def tokenize(text):
    return re.findall(r"[A-Za-z0-9_\\-]+", text.lower())

def bm25_search(db: Session, query, top_k=8):
    chunk_rows = db.query(DocumentChunk).join(Document).filter(Document.active.is_(True)).all()
    incident_rows = db.query(HistoricalIncident).all()
    records = []
    for row in chunk_rows:
        records.append({
            "chunk_code": row.chunk_code,
            "content": row.content,
            "metadata": {
                "document_id": row.document_id,
                "document_name": row.document.document_name,
                "document_type": row.document.document_type,
                "section": row.section,
                "page_number": row.page_number,
                "version": row.document.version
            }
        })
    for row in incident_rows:
        content = " ".join([
            row.incident_code or "",
            row.subject or "",
            row.description or "",
            row.category or "",
            row.asset_code or "",
            row.error_code or "",
            row.root_cause or "",
            row.resolution_steps or ""
        ])
        records.append({
            "chunk_code": f"incident:{row.incident_code}",
            "content": content,
            "metadata": {
                "document_name": row.incident_code,
                "document_type": "historical_incident",
                "section": "Incident record",
                "incident_code": row.incident_code,
                "error_code": row.error_code
            }
        })
    if not records:
        return []
    corpus = [tokenize(row["content"]) for row in records]
    model = BM25Okapi(corpus)
    scores = model.get_scores(tokenize(query))
    ranked = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)
    output = []
    for index in ranked[:top_k]:
        if scores[index] <= 0:
            continue
        item = dict(records[index])
        item["score"] = float(scores[index])
        output.append(item)
    return output
