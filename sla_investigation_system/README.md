# AI-Powered SLA Risk Analysis and Incident Investigation System

A basic modular implementation of the assessment using Python, FastAPI, PostgreSQL, SQLAlchemy, Pydantic, GPT-OSS-120B through an OpenAI-compatible endpoint, Sentence Transformers, Pinecone, LangChain text splitting, BM25, RRF, APScheduler, Streamlit, Pytest and Git.

## Features

- Synthetic tickets, assets, SLA policies and historical incidents.
- PDF and TXT document upload.
- Text extraction and chunking with document metadata.
- Sentence Transformer embeddings and Pinecone vector storage.
- PostgreSQL storage for document metadata and chunk text.
- Dense vector retrieval and BM25 keyword retrieval.
- Reciprocal Rank Fusion.
- LLM investigation reports with evidence and source metadata.
- Deterministic SLA calculation in Python.
- Ticket-specific persistent chat history.
- Investigation history in PostgreSQL.
- APScheduler-based SLA monitoring.
- Streamlit interface.
- Basic Pytest tests.

## Important behavior and limitations

The implementation keeps ticket priority, assignment, status and SLA records read-only during investigations. The LLM receives calculated SLA values from Python and is instructed not to calculate deadlines.

The sample SLA engine currently supports elapsed calendar minutes. Policies marked as business-hours-only are rejected until a business calendar and holiday rules are configured. This prevents incorrect deadline calculations.

The sample data is seeded automatically when the API starts for the first time. The seed data includes a few tickets, assets, SLA rules and historical incidents.

The system uses a single Pinecone index. Configure its dimension to match the selected embedding model. The default model produces 384-dimensional vectors.

Pinecone and the LLM endpoint require valid credentials. The application cannot perform vector search or AI generation until these are configured. BM25 uses the active document chunks stored in PostgreSQL.

For production use, add authentication and authorization, upload size limits, robust policy approval, database migrations, background job coordination, and stricter evidence validation.

## Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and provide:

- PostgreSQL connection string.
- Pinecone API key and index configuration.
- OpenAI-compatible endpoint URL.
- LLM API key and model name.

Do not commit `.env`.

### 4. Create PostgreSQL database

Create a database named `sla_investigation` in PostgreSQL, or use another database name and update `DATABASE_URL`.

Tables are created automatically when FastAPI starts.

### 5. Start the backend

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

### 6. Start Streamlit

Open another terminal:

```powershell
streamlit run streamlit_app/main.py
```

### 7. Run tests

```powershell
pytest -q
```

## Sample ticket IDs

- `INC-1001`: Critical production database outage.
- `INC-1002`: High-priority application login failure.
- `INC-1003`: Low-priority laptop battery issue.

Historical incident examples:

- `INC-0842`: Database service outage, error `DB-500`.
- `INC-0761`: Database connection failure, error `DB-CONN-01`.
- `INC-0710`: Authentication failure, error `AUTH-401`.

## Document upload

Use the Knowledge Base page in Streamlit or:

```powershell
curl.exe -X POST http://127.0.0.1:8000/documents/upload -F "document_type=sla_policy" -F "file=@SLA_Policy.pdf"
```

Supported document formats are PDF and TXT.

## Useful API endpoints

- `GET /tickets/`
- `GET /tickets/{ticket_code}`
- `GET /tickets/{ticket_code}/sla`
- `POST /documents/upload`
- `GET /documents/`
- `POST /investigations/{ticket_code}`
- `GET /investigations/{ticket_code}`
- `POST /chat/{ticket_code}`
- `GET /chat/{ticket_code}/history`
- `GET /admin/risks`

## Git workflow

```powershell
git checkout dev
git pull origin dev
git checkout -b feature/sla-investigation
git add .
git commit -m "Implement SLA investigation system"
git push -u origin feature/sla-investigation
```

Create a Pull Request from `feature/sla-investigation` into `dev`.

## Notes

- Never commit API keys, passwords, `.env`, virtual environments or private data.
- Pinecone vectors are hosted remotely and should not be committed.
- The scheduler is disabled by default. Set `SCHEDULER_ENABLED=true` to enable it.
- Run one scheduler instance when using multiple API workers.
