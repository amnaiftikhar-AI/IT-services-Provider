from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.database import initialize_database
from backend.app.routers import auth, clients, documents, sessions, drafts, preferences

app = FastAPI(title=settings.app_name, version="1.0.0")


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(documents.router)
app.include_router(sessions.router)
app.include_router(drafts.router)
app.include_router(preferences.router)
