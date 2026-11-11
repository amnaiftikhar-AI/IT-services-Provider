# Personalized Brand Voice & Content Intelligence Platform

A starter MVP for a multi-user AI writing platform. It includes FastAPI, PostgreSQL/pgvector, SQLAlchemy, Pydantic, Groq GPT-OSS-120B, Cloudflare BGE-M3 embeddings, LangChain chunking, Upstash Redis, Supabase Storage, Streamlit and Pytest.

## Included features

- JWT registration and login
- User-owned workspaces and client profiles
- PDF and TXT uploads
- Original file upload to a private Supabase Storage bucket
- Recursive structure-aware chunking
- Cloudflare BGE-M3 embeddings
- PostgreSQL pgvector storage and HNSW index
- User, client and company metadata filtering
- Personalized content generation
- Approved and rejected draft feedback
- Candidate preference extraction from draft edits
- Preference listing and deactivation
- Writing sessions with PostgreSQL persistence and Redis short-term context
- Streamlit interface
- Basic API tests

## Important scope notes

This is a runnable learning/MVP scaffold, not a production-certified multi-tenant system. Before production, add database migrations, robust rate limiting, refresh-token rotation, audit logging, malware scanning, comprehensive authorization tests, background ingestion jobs, retry handling, observability, and a formal company-admin workflow.

Company-wide documents are represented by `company_id` with a nullable `user_id`. This starter creates a default company per registered user. A real company deployment should add company membership and admin-managed company-wide guidelines.

The preference learner creates candidate preferences from edits. Candidates are not automatically treated as confirmed preferences. Review and activate them through the preferences endpoint after validation.

The Streamlit UI is a compact demonstration client. The FastAPI API is the main implementation surface.

## Requirements

- Python 3.11 or newer
- PostgreSQL with the pgvector extension available
- Accounts/API credentials for Groq, Cloudflare, Supabase and Upstash

## 1. Create services

### PostgreSQL

Use Supabase PostgreSQL or another PostgreSQL server where you can enable pgvector.

Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The application creates tables and the HNSW index at startup.

### Supabase Storage

1. Open your Supabase project.
2. Open Storage.
3. Create a bucket named `brand-voice-documents`.
4. Keep it private.
5. Copy the project URL and server-side service role key into `.env`.
6. Never put the service role key in Streamlit code or commit it to Git.

The backend uses the service role key to upload files. For production, use storage policies and user-scoped access or signed URLs.

### Cloudflare Workers AI

1. Open the Cloudflare dashboard.
2. Find your Account ID.
3. Create an API token with Workers AI access.
4. Set `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_EMBEDDING_MODEL`.
5. The configured model is `@cf/baai/bge-m3`.

The code calls the REST endpoint:
`https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/baai/bge-m3`

The application checks the returned embedding length against `EMBEDDING_DIMENSIONS`. If your account/model response differs, inspect the response and set the correct dimension consistently before ingesting data.

### GroqCloud

1. Create or open a GroqCloud account.
2. Create an API key.
3. Put it in `GROQ_API_KEY`.
4. Keep `GROQ_MODEL=openai/gpt-oss-120b` unless the model is unavailable to your account.

API usage and free-tier limits can change. Check your Groq console for current availability and limits.

### Upstash Redis

1. Create a Redis database in Upstash.
2. Copy the REST URL and REST token.
3. Put them in `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.

The Python SDK used here is the HTTP-based `upstash-redis` package.

## 2. Configure environment

Windows PowerShell:

```powershell
cd personalized_brand_voice_platform
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace every placeholder with your real credentials.

For Supabase PostgreSQL, use the connection string from Project Settings > Database. Prefer the connection string format compatible with psycopg, for example:

`postgresql+psycopg://postgres:YOUR_PASSWORD@HOST:5432/postgres`

URL-encode special characters in the database password.

## 3. Start the backend

From the project root:

```powershell
uvicorn backend.app.main:app --reload --port 8000
```

Open:
- API health: http://127.0.0.1:8000/health
- Swagger docs: http://127.0.0.1:8000/docs

At startup the application enables pgvector and creates the database tables/index.

## 4. Start Streamlit

Open a second PowerShell terminal, activate the same virtual environment, then run:

```powershell
streamlit run frontend/streamlit_app.py
```

The Streamlit app opens in your browser. Set `API_URL` in `.env` if your backend is hosted elsewhere.

## 5. First-use sequence

1. Register a user in Streamlit.
2. Log in.
3. Create a client profile.
4. Upload a PDF or TXT file and select its category.
5. Create a writing session and select a client.
6. Enter a request such as: `Write a concise, friendly follow-up email about the proposal.`
7. Edit the draft in the UI and submit the revised version.
8. Approve or reject the draft.
9. Review candidate preferences through the API or preferences panel.
10. Activate a candidate preference only after reviewing it.

## 6. API endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /clients`
- `GET /clients`
- `POST /documents/upload`
- `GET /documents`
- `POST /sessions`
- `GET /sessions`
- `PATCH /sessions/{session_id}`
- `POST /sessions/{session_id}/close`
- `POST /sessions/{session_id}/resume`
- `POST /drafts/generate`
- `POST /drafts/{draft_id}/feedback`
- `POST /drafts/{draft_id}/revise`
- `GET /preferences`
- `PATCH /preferences/{preference_id}`
- `DELETE /preferences/{preference_id}`

Use the Swagger page to inspect request schemas.

## 7. Test

With the virtual environment active:

```powershell
pytest -q
```

The included tests cover core utility behavior and API health. Add integration tests with a dedicated test database before relying on the application.

## 8. Git workflow

```powershell
git checkout -b feature/personalized-brand-voice
git add .
git commit -m "Build personalized brand voice platform"
git push -u origin feature/personalized-brand-voice
```

Open a Pull Request targeting `dev`.

Never commit `.env`, credentials, virtual environments, database dumps, or generated files.

## API connection guide

### PostgreSQL

- Create a PostgreSQL database.
- Enable pgvector with `CREATE EXTENSION IF NOT EXISTS vector;`.
- Copy the connection string into `DATABASE_URL`.
- The application connects through SQLAlchemy and psycopg.

### GroqCloud

- Create an API key in GroqCloud.
- Set `GROQ_API_KEY`.
- The code sends chat completion requests to Groq using `openai/gpt-oss-120b`.

### Cloudflare Workers AI

- Create a Cloudflare API token with Workers AI permissions.
- Set account ID and token.
- The code sends a list of text inputs and receives dense embeddings.

### Supabase Storage

- Create a private bucket.
- Set project URL and server-side key.
- The backend uploads the original document using its user/workspace path.

### Upstash Redis

- Create a Redis database.
- Copy REST URL and REST token.
- The backend stores recent messages under a user/session-specific key with TTL.

## Retrieval and chunking defaults

- Dense embeddings: BAAI/bge-m3 through Cloudflare
- Vector dimensions: configured by `EMBEDDING_DIMENSIONS`, default 1024
- Index: HNSW with cosine distance
- Chunking: recursive character splitting with document-aware separators
- Default chunk size: approximately 500 tokens, represented as 2,000 characters
- Default overlap: approximately 75 tokens, represented as 300 characters
- Retrieval: top 15 candidates, filtered by authenticated user, workspace, selected client and active status
- Final generation context: top 8 chunks
- Approved examples receive a ranking boost
- Rejected examples are excluded from positive writing context

Character counts are approximations of tokens. Tune chunk sizes using actual documents and retrieval evaluations.

## Security notes

- Use a strong random `SECRET_KEY`.
- Keep `.env` private.
- Never expose the Supabase service role key to the browser.
- Authenticate every API request.
- Validate resource ownership on every read/write operation.
- Keep company guidelines, user preferences and client documents in separate scopes.
- Do not treat generated preference extraction as ground truth without validation.
