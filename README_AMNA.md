# IT Services Provider — Amna's Knowledge Base & RAG Module

This folder is Amna's independently owned module for the group IT Service Desk project. It provides PDF/TXT ingestion, PostgreSQL metadata and chunks, BGE-M3 embeddings, FAISS dense search, BM25 keyword search, Reciprocal Rank Fusion, GPT-OSS-120B answers, ticket investigation suggestions, and persistent PostgreSQL chat history.

## 1. What belongs to Amna?

- `amna_rag/models.py`: KB documents, chunks, AI conversations and messages.
- `amna_rag/services/`: loading, splitting, indexing, retrieval, LLM and assistant logic.
- `amna_rag/routes/`: knowledge and AI APIs.
- `amna_frontend/`: Streamlit knowledge hub.
- `amna_knowledge_base/`: 20 synthetic technical documents.

Huda continues to own user, ticket, asset and SLA models/routes. The RAG API verifies Huda's JWT using the shared signing secret. For development only, `ALLOW_DEV_AUTH=true` accepts local identity headers; set it to `false` in production.

## 2. Setup (Windows PowerShell)

```powershell
cd it_services_amna
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-amna.txt
Copy-Item .env.amna.example .env
```

Edit `.env`: add your Groq API key and use the same JWT secret/algorithm as Huda's auth module. Set the PostgreSQL URL to your database.

Start PostgreSQL with Docker:

```powershell
docker compose -f docker-compose-amna.yml up -d postgres
```

If Huda already provides PostgreSQL, use that database instead; do not start a second database for the integrated project.

## 3. Load the 20 sample documents

Recommended: start the API and use the Streamlit Documents tab to upload every file from `amna_knowledge_base/pdf` and `amna_knowledge_base/txt`. Or seed the database before starting the API:

```powershell
python amna_scripts/seed_knowledge_base.py
```

The script uses the same ingestion service and skips duplicate files. If you run the seed script while the API is already running, restart the API so its in-memory FAISS index reloads the newly seeded vectors.

## 4. Run backend and frontend (two terminals)

Terminal 1:

```powershell
uvicorn amna_rag.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Terminal 2:

```powershell
streamlit run amna_frontend/app.py
```

Frontend: http://localhost:8501

For local demo, keep `ALLOW_DEV_AUTH=true`, select a development role in Streamlit and use a demo user ID. For integrated use, paste Huda's valid JWT and set `ALLOW_DEV_AUTH=false`.

## 5. Main API endpoints

- `POST /api/knowledge/upload` — support agent/admin multi-file upload.
- `GET /api/knowledge/documents` — list document metadata.
- `DELETE /api/knowledge/documents/{id}` — admin-only deletion and index rebuild.
- `POST /api/knowledge/reindex` — rebuild FAISS from PostgreSQL chunks.
- `POST /api/knowledge/search` — hybrid search.
- `POST /api/ai/chat` — RAG chat with persistent memory.
- `GET /api/ai/conversations` — restore permitted conversations.
- `POST /api/ai/ticket-assistance` — agent/admin ticket copilot.

## 6. How the RAG flow works

1. LangChain PDF/TXT loaders extract text and PDF page metadata.
2. Heading labels are attached to text blocks; recursive splitting uses heading/newline/paragraph/sentence separators with overlap.
3. Original files and metadata are stored in PostgreSQL. Each extracted section is a parent `KBSection` row; searchable `KBChunk` rows point to it through `parent_section_id`.
4. BGE-M3 embeds each chunk; FAISS stores vectors on disk.
5. BM25 ranks exact words, product names and error codes from PostgreSQL chunks.
6. The question is decomposed into focused searches; each search gets 8 dense and 8 BM25 candidates.
7. Reciprocal Rank Fusion combines ranked lists and returns up to 6 evidence chunks.
8. GPT-OSS-120B answers using retrieved evidence and conversation history. It must say when the knowledge base is insufficient.
9. Conversation messages and sources persist in PostgreSQL. FAISS can be rebuilt from PostgreSQL after restart.

## 7. Huda integration — exact connection

Huda's ticket detail page should call:

```http
POST /api/ai/ticket-assistance
Authorization: Bearer <Huda JWT>
Content-Type: application/json
```

```json
{
  "ticket_id": 42,
  "subject": "VPN connected but internal apps unavailable",
  "description": "VPN shows connected. Internal portal does not load. Error VPN-204.",
  "category": "Network",
  "priority": "High",
  "asset": {"asset_id": 12, "name": "Employee Laptop"}
}
```

The response contains `ticket_id`, `issue_summary`, `troubleshooting_steps`, `sources`, `missing_information`, `escalation_recommended`, and `escalation_reason`. Huda's frontend displays these fields inside the ticket detail page. The endpoint never updates ticket records.

**Shared auth requirement:** this module expects Huda's JWT to contain `sub` (or `user_id`) and `role`. If her claim names differ, adjust only `amna_rag/dependencies.py` to match her token. Use one shared PostgreSQL database and coordinate schema migrations before merging. Add the packages in `requirements-amna.txt` to Huda's shared `requirements.txt`, and append the ignore rules from `.gitignore.amna` to the repository's existing `.gitignore` rather than replacing it.

## 8. Exact place where Huda connects your code

Keep this module inside the shared repository using its separate `amna_rag/`, `amna_frontend/`, `amna_knowledge_base/`, `amna_data/` and `amna_scripts/` folders. This avoids overwriting Huda's `backend/main.py`, `backend/models.py`, `backend/database.py` and ticket routes.

In Huda's existing `backend/main.py`, add the following imports and router registrations (keep her existing imports and routers):

```python
from amna_rag.routes import knowledge_routes, ai_routes
from amna_rag.database import Base as AmnaBase, engine as amna_engine

app.include_router(knowledge_routes.router)
app.include_router(ai_routes.router)

@app.on_event("startup")
def create_amna_tables():
    AmnaBase.metadata.create_all(bind=amna_engine)
```

Set the same `DATABASE_URL` in both modules so the RAG tables and Huda's ticket tables live in the same PostgreSQL database. Set `JWT_SECRET_KEY` to Huda's actual JWT signing secret and confirm that her token has `sub` (or `user_id`) and `role` claims. If Huda's claims differ, change `amna_rag/dependencies.py` only. For production, set `ALLOW_DEV_AUTH=false`.

In Huda's ticket-detail Streamlit page, put an **Ask AI to investigate** button after the ticket description. Example call:

```python
import requests

if st.button("Ask AI to investigate"):
    response = requests.post(
        "http://127.0.0.1:8000/api/ai/ticket-assistance",
        headers={"Authorization": f"Bearer {huda_jwt_token}"},
        json={
            "ticket_id": ticket["id"],
            "subject": ticket["subject"],
            "description": ticket["description"],
            "category": ticket["category"],
            "priority": ticket["priority"],
            "asset": ticket.get("asset"),
        },
        timeout=180,
    )
    if response.ok:
        ai_result = response.json()
        st.subheader("AI investigation")
        st.write(ai_result["issue_summary"])
        for step in ai_result["troubleshooting_steps"]:
            st.markdown(f"- {step}")
        st.write("Sources:", ai_result["sources"])
        st.write("Missing information:", ai_result["missing_information"])
        st.write("Escalation:", ai_result["escalation_reason"])
    else:
        st.error(response.text)
```

Use Huda's actual ticket field names if they differ. The AI endpoint only returns suggestions; Huda's existing ticket update route remains responsible for any status, assignment or resolution changes.

## 9. Git workflow

```powershell
git checkout dev
git pull origin dev
git checkout -b feature/amna-document-ingestion
# add this module's files
git add .
git commit -m "Add knowledge base document ingestion"
git push -u origin feature/amna-document-ingestion
```

Create a PR into `dev`. Then repeat for `feature/amna-hybrid-retrieval` and `feature/amna-ai-assistant`. Do not commit `.env`, API keys, the FAISS index or uploads.

## Notes

- BGE-M3 downloads model weights on first run and can use significant RAM/disk space.
- The first embedding/index build can take several minutes on CPU.
- FAISS is a rebuildable local index; PostgreSQL is the durable source of truth for document metadata and chunks.
- This starter creates tables with SQLAlchemy `create_all`. For the shared production schema, coordinate Alembic migrations with Huda.
- This project is a development baseline; run the included tests and verify the JWT claims against Huda's actual implementation before integration.
