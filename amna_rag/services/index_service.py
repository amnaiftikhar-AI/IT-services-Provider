from pathlib import Path
from threading import RLock
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from amna_rag.config import settings
from amna_rag.services.embedding_service import get_embeddings

_lock = RLock()
_vector_store = None

def _index_dir() -> Path:
    path = Path(settings.faiss_index_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_index():
    global _vector_store
    with _lock:
        index_file = _index_dir() / "index.faiss"
        if index_file.exists():
            _vector_store = FAISS.load_local(str(_index_dir()), get_embeddings(), allow_dangerous_deserialization=True)
        return _vector_store

def rebuild_index(chunks: list[dict]):
    global _vector_store
    with _lock:
        if not chunks:
            _vector_store = None
            for file in _index_dir().glob("*"):
                if file.is_file(): file.unlink()
            return 0
        docs = [Document(page_content=x["content"], metadata=x["metadata"]) for x in chunks]
        _vector_store = FAISS.from_documents(docs, get_embeddings())
        _vector_store.save_local(str(_index_dir()))
        return len(docs)

def add_documents(documents: list[Document]):
    global _vector_store
    with _lock:
        if not documents:
            return
        if _vector_store is None:
            _vector_store = FAISS.from_documents(documents, get_embeddings())
        else:
            _vector_store.add_documents(documents)
        _vector_store.save_local(str(_index_dir()))

def dense_search(question: str, k: int = 8):
    global _vector_store
    with _lock:
        if _vector_store is None:
            load_index()
        if _vector_store is None:
            return []
        return _vector_store.similarity_search_with_score(question, k=k)
