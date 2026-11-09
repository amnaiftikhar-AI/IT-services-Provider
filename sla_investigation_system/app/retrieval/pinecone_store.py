from pinecone import Pinecone, ServerlessSpec
from app.config import settings

_client = None
_index = None

def get_index():
    global _client, _index
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not configured.")
    if _index is None:
        _client = Pinecone(api_key=settings.pinecone_api_key)
        names = [item["name"] for item in _client.list_indexes()]
        if settings.pinecone_index_name not in names:
            _client.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region)
            )
        _index = _client.Index(settings.pinecone_index_name)
    return _index

def upsert_vectors(vectors):
    get_index().upsert(vectors=vectors)

def delete_document_vectors(document_id):
    get_index().delete(filter={"document_id": document_id})

def dense_search(vector, top_k=8):
    result = get_index().query(
        vector=vector,
        top_k=top_k,
        include_metadata=True
    )
    return [
        {
            "chunk_code": match["id"],
            "score": match.get("score", 0),
            "content": match.get("metadata", {}).get("content", ""),
            "metadata": match.get("metadata", {})
        }
        for match in result.get("matches", [])
    ]
