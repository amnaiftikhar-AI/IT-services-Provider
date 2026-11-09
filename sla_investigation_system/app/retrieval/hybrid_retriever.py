from app.ingestion.embedder import embed_query
from app.retrieval.pinecone_store import dense_search
from app.retrieval.bm25_search import bm25_search
from app.retrieval.rrf import reciprocal_rank_fusion

def hybrid_search(db, query, top_k=8):
    vector = embed_query(query)
    dense_results = dense_search(vector, top_k=top_k)
    keyword_results = bm25_search(db, query, top_k=top_k)
    return reciprocal_rank_fusion(dense_results, keyword_results, limit=top_k)
