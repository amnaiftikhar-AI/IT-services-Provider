from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from amna_rag.database import Base, engine, SessionLocal
from amna_rag.routes import knowledge_routes, ai_routes
from amna_rag.services.index_service import load_index
from amna_rag.services.ingestion_service import rebuild_all
from amna_rag.models import KBChunk
from amna_rag.config import settings

app = FastAPI(title=settings.app_name, version="1.0.0", description="Amna's independently owned Knowledge Base and AI RAG module")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(knowledge_routes.router)
app.include_router(ai_routes.router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.faiss_index_path).mkdir(parents=True, exist_ok=True)
    if not load_index():
        db = SessionLocal()
        try:
            if db.query(KBChunk).first(): rebuild_all(db)
        finally: db.close()

@app.get("/health")
def health(): return {"status": "ok", "module": "amna-rag"}
