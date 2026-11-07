from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from amna_rag.models import KBChunk, KBDocument
from amna_rag.services.index_service import dense_search
import re

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

def tokenize(text: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(text)]

def bm25_search(db: Session, question: str, k: int = 8, document_type: str | None = None, department: str | None = None):
    query = db.query(KBChunk, KBDocument).join(KBDocument, KBChunk.document_id == KBDocument.id)
    if document_type: query = query.filter(KBDocument.document_type == document_type)
    if department: query = query.filter(KBDocument.department == department)
    rows = query.all()
    if not rows: return []
    corpus = [tokenize(chunk.content) for chunk, _ in rows]
    scores = BM25Okapi(corpus).get_scores(tokenize(question))
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
    return [{"chunk": rows[i][0], "document": rows[i][1], "score": float(score)} for i, score in ranked if score > 0]

def hybrid_search(db: Session, question: str, dense_k: int = 8, bm25_k: int = 8, final_k: int = 6, document_type: str | None = None, department: str | None = None):
    # Dense FAISS results use their metadata; filters are also applied after retrieval.
    dense = dense_search(question, dense_k)
    keyword = bm25_search(db, question, bm25_k, document_type, department)
    ranked = {}
    for rank, (doc, distance) in enumerate(dense, start=1):
        meta = doc.metadata
        if document_type and meta.get("document_type") != document_type: continue
        if department and meta.get("department") != department: continue
        key = str(meta.get("chunk_id") or (meta.get("source"), meta.get("page"), doc.page_content[:80]))
        ranked.setdefault(key, {"content": doc.page_content, "metadata": meta, "rrf": 0.0, "dense_rank": None, "bm25_rank": None})
        ranked[key]["rrf"] += 1 / (60 + rank)
        ranked[key]["dense_rank"] = rank
    for rank, item in enumerate(keyword, start=1):
        chunk, document = item["chunk"], item["document"]
        key = str(chunk.id)
        ranked.setdefault(key, {"content": chunk.content, "metadata": {"chunk_id": chunk.id, "source": document.filename, "page": chunk.page_number, "section": chunk.parent_section, "document_type": document.document_type, "department": document.department}, "rrf": 0.0, "dense_rank": None, "bm25_rank": None})
        ranked[key]["rrf"] += 1 / (60 + rank)
        ranked[key]["bm25_rank"] = rank
    return sorted(ranked.values(), key=lambda x: x["rrf"], reverse=True)[:final_k]
