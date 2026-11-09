from sentence_transformers import SentenceTransformer
from app.config import settings

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model

def embed_texts(texts):
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()

def embed_query(text):
    return embed_texts([text])[0]
