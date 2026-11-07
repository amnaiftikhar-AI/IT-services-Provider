from pathlib import Path
from amna_rag.database import Base, engine, SessionLocal
from amna_rag.services.ingestion_service import ingest_file

ROOT = Path(__file__).resolve().parents[1]
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    for folder in [ROOT / "amna_knowledge_base" / "pdf", ROOT / "amna_knowledge_base" / "txt"]:
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() not in {".pdf", ".txt"}: continue
            try:
                doc, count = ingest_file(db, path.name, path.read_bytes(), "seed-script", "Technical Guide", "IT", "General IT")
                print(f"Added {doc.filename}: {count} chunks")
            except ValueError as exc:
                print(f"Skipped {path.name}: {exc}")
finally:
    db.close()
