from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from amna_rag.config import settings

@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
