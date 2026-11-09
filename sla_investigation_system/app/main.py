from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine, SessionLocal
from app.config import settings
from app.services.seed_service import seed_data
from app.routers import tickets, documents, investigations, chat, admin
from app.scheduler.sla_monitor import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
    if settings.scheduler_enabled:
        start_scheduler(settings.scheduler_interval_minutes)
    yield
    if settings.scheduler_enabled:
        stop_scheduler()

app = FastAPI(
    title="AI-Powered SLA Risk Analysis and Incident Investigation System",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(tickets.router)
app.include_router(documents.router)
app.include_router(investigations.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "SLA Investigation API is running"}
