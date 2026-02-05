# NeuroLink Agent Documentation

> **Last Updated:** 2026-02-05
> **Current Phase:** Phase 2 - The Processor (Completed)
> **Status:** Functional — AI summarization, embeddings, and semantic search operational

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [System Architecture](system/architecture.md) | Full system design: components, data flow, database schemas (SQLite + Supabase), AI processing pipeline, tech stack, API endpoints |
| [Critical Errors & Fixes](system/critical-errors.md) | Known issues, errors encountered, and solutions |
| [Local Development Setup](sop/local-dev.md) | How to set up and run the project locally (backend, extension, OpenAI, Supabase) |

---

## Project Overview

**NeuroLink** is a Personal Knowledge Management (PKM) system that:
1. **Collects** Twitter/X bookmarks via Chrome extension
2. **Processes** content with AI (OpenAI GPT-4o-mini summaries + text-embedding-3-small vectors)
3. **Stores** structured data in SQLite, vector embeddings in Supabase pgvector
4. **Searches** saved knowledge via semantic similarity search with filters
5. **(Future)** Provides RAG-based chat interface

---

## Current Architecture

```
Extension → POST /api/ingest → SQLite → BackgroundTask
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              OpenAI GPT          OpenAI Embeddings
                              (Summary)           (Vectors)
                                    │                   │
                                    ▼                   ▼
                              SQLite              Supabase pgvector
                              (summary field)     (item_embeddings table)
```

**Key Design:** Content is extracted by the Chrome extension using the user's authenticated session. AI processing happens in background tasks after ingest.

---

## Project Structure

```
neurolink/
├── extension/                 # Chrome Extension (Manifest V3)
│   ├── manifest.json         # Extension config
│   ├── popup.html/js         # Extension UI
│   └── content.js            # Page scraping logic (MAIN FILE)
│
├── backend/                   # FastAPI Backend
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── api/routes.py     # API endpoints (ingest, items, processing, search)
│   │   ├── models/item.py    # SQLAlchemy model (with AI processing fields)
│   │   ├── schemas/ingest.py # Pydantic schemas
│   │   ├── services/
│   │   │   ├── openai_service.py  # OpenAI API (summaries + embeddings)
│   │   │   ├── vector_service.py  # Supabase pgvector client
│   │   │   └── processor.py      # Background processing orchestrator
│   │   └── core/
│   │       ├── config.py     # Settings (DB, OpenAI, Supabase)
│   │       └── database.py   # DB connection
│   ├── migrations/
│   │   └── supabase/
│   │       └── 001_vector_setup.sql  # Supabase table + function setup
│   ├── data/                 # SQLite database location
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                  # Local config (git-ignored)
│
└── .agent/                    # Documentation
    ├── README.md             # This file — documentation index
    ├── system/
    │   ├── architecture.md   # Full system design & schemas
    │   └── critical-errors.md# Error history & fixes
    └── sop/
        └── local-dev.md      # Development setup guide
```

---

## API Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (includes `ai_enabled` flag) |
| POST | `/api/ingest` | Ingest items from extension |
| GET | `/api/items` | List items (`?status=`, `?limit=`, `?offset=`) |
| GET | `/api/items/{id}` | Get single item |

### Processing (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/items/{id}/status` | Processing status |
| POST | `/api/items/{id}/reprocess` | Trigger reprocessing (`?force=true`) |
| GET | `/api/processing/stats` | Counts by summary/embedding status |
| POST | `/api/processing/run-all` | Bulk process all pending items |
| POST | `/api/search/semantic` | Semantic search with filters |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Extension | Chrome Manifest V3, Vanilla JS |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (structured data) |
| Vector DB | Supabase pgvector (embeddings, HNSW index) |
| AI / LLM | OpenAI GPT-4o-mini (summaries), text-embedding-3-small (embeddings) |
| Retry | tenacity (exponential backoff) |
| Validation | Pydantic v2 |

---

## Phase Roadmap

### Phase 1: The Collector (Completed)
- [x] Chrome Extension for scraping bookmarks
- [x] FastAPI Backend for storage
- [x] Content type detection (tweet vs article)
- [x] Metadata extraction (images, quotes, videos)
- [x] Virtual scrolling fix (incremental capture)

### Phase 2: The Processor (Completed)
- [x] OpenAI summarization
- [x] Embedding generation + Supabase pgvector storage
- [x] Background processing pipeline with retry
- [x] Semantic search with content_type and date filters
- [x] Smart reprocess (content hash comparison)
- [x] Bulk processing + status/stats endpoints

### Phase 3: The Oracle (Future)
- [ ] RAG-based chat interface
- [ ] Multi-turn conversation with knowledge base
- [ ] Advanced search UI

---

## Quick Start

```bash
# 1. Start backend
cd neurolink/backend
source venv/bin/activate
uvicorn app.main:app --reload

# 2. Load extension
# Go to chrome://extensions → Developer mode → Load unpacked → select extension/

# 3. Use
# Go to twitter.com/i/bookmarks → Click extension → Sync Bookmarks

# 4. Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/processing/stats
```

---

## Key Files to Understand

1. **`extension/content.js`** — Main scraping logic, content type detection, metadata extraction
2. **`backend/app/api/routes.py`** — All API endpoints, ingest + background task triggers
3. **`backend/app/services/processor.py`** — Background processing orchestrator (summary → embedding → Supabase)
4. **`backend/app/services/openai_service.py`** — OpenAI API client with retry logic
5. **`backend/app/services/vector_service.py`** — Supabase pgvector client
6. **`backend/app/models/item.py`** — Database model with all fields
7. **`backend/app/core/config.py`** — All configuration settings

---

## For Next Agent

**Priority for Phase 3:**
1. Design RAG chat interface (likely needs a new `/api/chat` endpoint)
2. Multi-turn conversation support with context window management
3. Consider whether to add a frontend UI

**See:** [System Architecture](system/architecture.md) for full technical details.
