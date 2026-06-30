# Multi-Agent Research & Report Generation Platform

A production-grade AI research team in your browser: enter a topic, and ten
specialized AI agents collaborate to search the web, verify facts, build a
knowledge base, and produce a fully-cited professional report — complete
with an executive summary and a branded PDF export.

Built entirely on **free and open-source tools** — no paid APIs required to run it.

---

## ✨ What it does

1. You enter a research topic or question (e.g. *"Latest advancements in AI Agents"*)
2. The **Research Coordinator** breaks it into focused subtopics
3. The **Web Research Agent** searches the internet (Tavily + DuckDuckGo)
4. The **Content Extraction Agent** scrapes and cleans each source
5. The **Fact Verification Agent** cross-checks claims and scores credibility
6. The **Knowledge Base Agent** embeds and stores everything in ChromaDB (RAG)
7. The **Summarization Agent** writes short / medium / detailed summaries
8. The **Report Writer Agent** drafts the full report (abstract → conclusion)
9. The **Executive Summary Agent** writes a 1-page business brief
10. The **Citation Agent** generates APA / MLA / IEEE references
11. The **PDF Generation Agent** exports a branded, downloadable PDF

All of this is visible live in the **Research Workspace**, with per-agent
status, streaming logs, a sources panel with credibility scores, and an
analytics dashboard (source distribution, timeline, confidence scores,
topic clusters).

---

## 🏗️ Architecture

```
frontend/   Next.js 15 + TypeScript + Tailwind + shadcn/ui + Recharts
backend/    FastAPI + Python 3.12 + CrewAI + ChromaDB + PostgreSQL + Redis
```

```
User Query
   │
   ▼
Research Coordinator ──▶ Web Research ──▶ Content Extraction
   │                                              │
   ▼                                              ▼
PDF Generation ◀── Citation ◀── Executive    Fact Verification
   ▲                Summary ◀── Report   ◀──        │
   │                              Writer ◀── Summarization ◀── Knowledge Base
   └──────────────────────────────────────────────────────────────┘
```

See `crews/research_crew.py` for the exact orchestration logic.

### Tech stack (all free-tier / open-source)

| Layer            | Choice                                                        |
|-------------------|----------------------------------------------------------------|
| Frontend          | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Recharts      |
| Backend           | FastAPI, Python 3.12                                           |
| AI orchestration  | CrewAI                                                          |
| LLMs (primary)    | OpenRouter free models (DeepSeek V3/R1, Qwen 3, Llama 3.3, Gemma 3) |
| LLMs (fallback)   | Groq free API                                                  |
| Vector DB         | ChromaDB                                                        |
| Embeddings        | `BAAI/bge-small-en-v1.5` (local, free, via sentence-transformers) |
| Database          | PostgreSQL (Neon free tier works great)                         |
| Auth              | Clerk (free tier)                                               |
| Caching / Queue   | Redis + Celery                                                  |
| PDF generation    | ReportLab + matplotlib                                          |
| Web search        | Tavily (free tier) + DuckDuckGo (no key needed)                 |

---

## 🚀 Quick start (Docker)

```bash
# 1. Clone and configure environment
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# Fill in API keys (see "Getting free API keys" below)

# 2. Start everything
docker compose up --build

# 3. Open the app
# Frontend:        http://localhost:3000
# API docs:         http://localhost:8000/api/docs
```

On first boot the backend auto-creates tables in development mode. For
production, run Alembic migrations instead (see below).

---

## 🔑 Getting free API keys

| Service     | Free tier             | Get it at                                  |
|-------------|------------------------|---------------------------------------------|
| OpenRouter  | Free models, no card   | https://openrouter.ai/keys                  |
| Groq        | Generous free tier     | https://console.groq.com/keys               |
| Tavily      | 1,000 free searches/mo | https://tavily.com                           |
| Clerk       | Free up to 10k MAUs    | https://dashboard.clerk.com                  |
| Neon        | Free Postgres          | https://neon.tech                            |

DuckDuckGo search requires **no API key at all** and is used automatically
as a fallback if Tavily is unavailable.

---

## 🧑‍💻 Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --break-system-packages
cp .env.example .env   # fill in your keys

# Run Postgres, Redis, ChromaDB separately, or via:
docker compose up postgres redis chromadb

uvicorn main:app --reload
```

### Database migrations (production)

```bash
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in Clerk keys
npm run dev
```

### Background worker (optional — for Celery-based dispatch)

```bash
cd backend
celery -A core.celery_app worker --loglevel=info
```

---

## 🛡️ Production hardening notes

This codebase has been through a real hardening pass — not just written, but
actually installed, imported, and exercised against a live PostgreSQL
database to catch the kind of bugs that only show up at runtime. Specifics:

- **Background execution is real Celery, not a `BackgroundTasks` shortcut.**
  `POST /api/research` dispatches via `tasks.research_tasks.run_research_task.delay(...)`,
  so an API process restart never silently drops an in-flight research run.
- **Settings persist for real.** `GET`/`PUT /api/settings` read/write a
  `user_settings` table; bring-your-own API keys are encrypted at rest
  (Fernet, keyed off `SECRET_KEY` — see `core/crypto.py`) and the API never
  returns key values back, only `*_key_configured` booleans.
- **Follow-up research actually re-invokes the LLM.** `POST
  /api/report/{id}/follow-up` retrieves relevant knowledge-base chunks via
  RAG and re-runs the Report Writer agent with the instruction and prior
  report as context — it doesn't just append a text note.
- **Per-user, per-IP rate limiting on the expensive endpoint.** Starting a
  research run is capped at 5/minute per IP (on top of the global 30/minute
  default) and at `MAX_CONCURRENT_RESEARCH_SESSIONS` in-flight runs per user,
  since each request fires off 10+ chained LLM/search calls.
- **Lazy service connections.** ChromaDB and the embedding model connect on
  first actual use, not at import time — an earlier version eagerly opened a
  ChromaDB connection as a module-level side effect, which meant the entire
  API would fail to even start if Chroma was still booting.
- **Request correlation IDs + security headers** on every response
  (`core/request_context.py`, `main.py` middleware) — `X-Request-ID`,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS in
  non-dev environments.
- **The dependency tree was broken and is now fixed.** The original
  `requirements.txt` pinned `crewai==0.65.2` alongside `langchain==0.3.1` —
  versions that are mutually incompatible, so `pip install` failed outright.
  `agents/llm_provider.py` now builds on CrewAI's own `BaseLLM`/litellm
  extension point instead of a LangChain shim, dropping the langchain
  dependency chain entirely. Verified: `pip install -r requirements.txt`
  succeeds, and the resulting `ResilientLLM` is a real working `crewai.LLM`
  fallback wrapper (OpenRouter → Groq), confirmed by actually constructing
  one and attaching it to a real `crewai.Agent`.
- **The initial Alembic migration is hand-verified, not just generated.**
  Every column in `migrations/versions/0001_initial_schema.py` was
  diffed programmatically against the actual ORM model field names (an
  earlier draft had several silent typos — e.g. `openrouter_api_key_encrypted`
  in the migration vs. `openrouter_key_encrypted` on the model). Verified:
  `alembic upgrade head` and `alembic downgrade base` both run cleanly
  against a real Postgres 16 instance.
- **A real integration test exercises real Postgres.** Unlike the unit
  tests (which mock the DB), `tests/test_pipeline_integration.py` runs the
  full `ResearchCrewRunner.run()` orchestration against an actual database
  via `docker-compose.test.yml` (`make test-integration`) — JSONB columns,
  UUID foreign keys, and cascading deletes all verified to round-trip
  correctly, with only the LLM/search network boundary mocked.
- **Frontend: real type-check + lint + production build, zero errors.**
  Next.js was also bumped off `15.0.3` (a version with a disclosed CVE) to
  the latest patched 15.x release.

What's still a known gap, by design rather than oversight: there's no
distributed tracing/metrics pipeline (just structured logs with correlation
IDs), no per-user cost dashboards beyond the daily concurrent-session cap,
and the free-tier LLM providers this is built around have real rate limits —
this architecture is sized for personal/small-team use, not high-concurrency
production traffic, without moving to paid LLM tiers.

## 📁 Folder structure

```
backend/
├── agents/        # The 10 CrewAI agents
├── api/           # FastAPI route modules
├── core/          # Config, security, Celery app
├── crews/         # Orchestration (research_crew.py)
├── database/      # Async SQLAlchemy connection
├── migrations/    # Alembic migrations
├── models/        # SQLAlchemy ORM models
├── rag/           # ChromaDB + embedding services
├── schemas/       # Pydantic request/response schemas
├── services/      # PDF generation, etc.
├── tasks/         # Celery tasks
└── tools/         # CrewAI tools (search, scraping, RAG)

frontend/
├── app/           # Next.js App Router pages
├── components/    # UI primitives + layout components
└── lib/           # API client, types, utilities
```

---

## 🌐 Deployment

| Component | Suggested free host |
|-----------|----------------------|
| Frontend  | Vercel                |
| Backend   | Render                |
| Database  | Neon (PostgreSQL)      |
| Vector DB | Render disk / ChromaDB Cloud free tier |
| Redis     | Render free Redis / Upstash free tier |

Set the same environment variables from `backend/.env.example` and
`frontend/.env.local.example` in your hosting provider's dashboard.

---

## 🔒 Security notes

- All API routes require a valid Clerk JWT (`core/security.py`)
- Rate limiting via `slowapi` (configurable per-minute limit)
- Role-based access control available via `require_role()`
- Secrets are never committed — `.env` files are gitignored
- CORS is restricted to `ALLOWED_ORIGINS`

---

## 🧪 Testing

```bash
# Unit tests — pure logic, no DB/network required, runs in seconds
cd backend
pytest --cov --ignore=tests/test_pipeline_integration.py

# Integration test — exercises a real disposable Postgres instance
make test-integration
```

---

## 📄 License

This project is provided as a reference implementation/scaffold. Adapt
freely for your own use.
