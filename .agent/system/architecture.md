# NeuroLink Architecture

> **Last Updated:** 2026-02-05
> **Related Docs:** [README](../README.md) | [Critical Errors](critical-errors.md) | [Local Dev Setup](../sop/local-dev.md)

---

## Overview

NeuroLink is a Personal Knowledge Management (PKM) system that:
1. **Collects** Twitter/X bookmarks via Chrome extension (authenticated session)
2. **Processes** content with AI — generates summaries (OpenAI GPT) and vector embeddings
3. **Stores** structured data in SQLite, vector embeddings in Supabase pgvector
4. **Searches** saved knowledge via semantic search
5. **(Future)** Provides RAG-based chat interface for knowledge retrieval

---

## System Components

### 1. Chrome Extension
- **Location:** `extension/`
- **Purpose:** Scrapes Twitter bookmarks directly from authenticated browser session
- **Key Files:**
  - `manifest.json` - Extension configuration (Manifest V3)
  - `popup.html/js` - Extension UI and event handlers
  - `content.js` - Main scraping logic, content extraction, metadata detection

### 2. FastAPI Backend
- **Location:** `backend/`
- **Purpose:** API server for data ingestion, AI processing, and semantic search
- **Key Files:**
  - `app/main.py` - FastAPI application with CORS configuration
  - `app/api/routes.py` - API endpoints (ingest, items, processing, search)
  - `app/models/item.py` - SQLAlchemy ORM model with AI processing fields
  - `app/schemas/ingest.py` - Pydantic validation schemas
  - `app/core/database.py` - SQLAlchemy engine and session management
  - `app/core/config.py` - Environment configuration (DB, OpenAI, Supabase)

### 3. AI Processing Services
- **Location:** `backend/app/services/`
- **Purpose:** Background AI summarization and embedding generation
- **Key Files:**
  - `openai_service.py` - OpenAI API client (summaries via GPT-4o-mini, embeddings via text-embedding-3-small)
  - `vector_service.py` - Supabase pgvector client (upsert, search, delete embeddings)
  - `processor.py` - Background task orchestrator (content selection, hash comparison, retry logic)

### 4. SQLite Database
- **Location:** `backend/data/neurolink.db`
- **Purpose:** Persistent storage for saved items, summaries, and processing state

### 5. Supabase pgvector (External)
- **Purpose:** Vector storage and similarity search for embeddings
- **Table:** `item_embeddings` with HNSW index
- **Function:** `match_items()` for filtered semantic search

---

## Data Flow

### Ingest + Processing Flow

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

### Flow Steps:
1. User opens Twitter bookmarks page (`twitter.com/i/bookmarks`)
2. User clicks extension → "Sync Bookmarks"
3. Extension performs **incremental scrolling** (800px steps) to handle Twitter's virtual DOM
4. After each scroll increment:
   - Immediately captures visible items before they're virtualized out
   - Clicks "Show more" buttons to expand truncated text
   - Detects content type (tweet vs article)
   - Extracts metadata (images, videos, quotes, etc.)
5. Extension sends batch to backend `POST /api/ingest`
6. Backend validates API key is configured, checks for duplicates, stores new items
7. Background tasks are triggered for each item with content:
   - **Summary generation:** Best content selected → GPT-4o-mini → 1-2 sentence summary
   - **Embedding generation:** Summary + content concatenated → text-embedding-3-small → 1536-dim vector
   - **Vector storage:** Embedding upserted to Supabase pgvector with content preview

**Content Selection Priority:** `thread_content` → `full_content` → `raw_preview` → article fields from `extra_data`

**IMPORTANT:** Twitter uses virtual scrolling - only ~6-11 items exist in DOM at once. Items are removed from DOM when scrolled out of view. The incremental capture strategy ensures items are captured before they disappear.

### Semantic Search Flow

```
User query → OpenAI Embedding → Supabase match_items() → Item IDs → SQLite full items
```

---

## Database Schema

### SQLite: `saved_items` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| source_url | VARCHAR(2048) | Unique tweet URL (indexed) |
| source_platform | VARCHAR(50) | "twitter" (for future multi-platform support) |
| content_type | VARCHAR(50) | "tweet" or "article" |
| raw_preview | TEXT | Preview text from extension |
| full_content | TEXT | Full tweet/article text |
| thread_content | TEXT | Thread context |
| extra_data | JSON/TEXT | Metadata object (custom JSONType) |
| status | VARCHAR(20) | "pending", "fetched", "fetch_failed" |
| fetch_attempts | INTEGER | Retry counter |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| **summary** | **TEXT** | AI-generated summary (1-2 sentences) |
| **summary_model** | **VARCHAR(50)** | Model used (e.g. "gpt-4o-mini") |
| **summary_status** | **VARCHAR(20)** | "pending", "processing", "completed", "failed" |
| **embedding_status** | **VARCHAR(20)** | "pending", "processing", "completed", "failed" |
| **embedding_id** | **BIGINT** | ID in Supabase item_embeddings table |
| **processing_error** | **TEXT** | Error message if processing failed |
| **processed_at** | **DATETIME** | When AI processing completed |
| **content_hash** | **VARCHAR(64)** | SHA-256 hash for smart reprocess |

**Bold** = Added in Phase 2.

### `extra_data` JSON Structure

```json
{
  "content_type": "tweet" | "article",
  "has_images": boolean,
  "image_count": number,
  "image_urls": string[],
  "has_video": boolean,
  "has_quote": boolean,
  "quoted_author": string | null,
  "quoted_text": string | null,
  "has_show_more": boolean,
  "article_title": string | null,
  "article_description": string | null,
  "article_cover_url": string | null
}
```

### Supabase: `item_embeddings` Table

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Auto-generated identity |
| neurolink_item_id | BIGINT | FK to SQLite saved_items.id (unique) |
| source_url | TEXT | Original content URL |
| content_type | TEXT | "tweet" or "article" |
| content_preview | TEXT | First 500 chars of content |
| embedding | vector(1536) | OpenAI text-embedding-3-small vector |
| created_at | TIMESTAMPTZ | Auto-generated |

**Indexes:**
- `item_embeddings_neurolink_item_id_unique` — Unique on neurolink_item_id
- `item_embeddings_embedding_idx` — HNSW index with vector_cosine_ops

**SQL Function:** `match_items(query_embedding, match_threshold, match_count, filter_content_type, filter_after, filter_before)` — Cosine similarity search with optional filters.

---

## API Endpoints

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (includes `ai_enabled` flag) |
| POST | `/api/ingest` | Ingest items from extension (requires API key) |
| GET | `/api/items` | List saved items (`?status=`, `?limit=`, `?offset=`) |
| GET | `/api/items/{id}` | Get single item by ID |

### Processing Endpoints (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/items/{id}/status` | Processing status for an item |
| POST | `/api/items/{id}/reprocess` | Reprocess item (`?force=true` to skip hash check) |
| GET | `/api/processing/stats` | Summary/embedding counts by status |
| POST | `/api/processing/run-all` | Bulk process all pending/failed items |

### Search Endpoints (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/search/semantic` | Semantic search with filters |

**Semantic Search Request:**
```json
{
  "query": "string",
  "limit": 10,
  "threshold": 0.7,
  "content_type": "tweet" | "article" | null,
  "after": "ISO datetime" | null,
  "before": "ISO datetime" | null
}
```

### Debug Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/debug` | Save debug snapshot from extension |
| GET | `/api/debug/latest` | Get most recent debug snapshot |
| GET | `/api/debug/list` | List available debug snapshots |
| GET | `/api/debug/{id}` | Get specific snapshot |

---

## AI Processing Pipeline

### Architecture

- **Trigger:** Background tasks via FastAPI `BackgroundTasks` (triggered on ingest)
- **Session safety:** Each background task creates its own `SessionLocal()` — the request DB session is NOT passed to background tasks
- **Rate limiting:** 0.5s delay between OpenAI API calls (`RATE_LIMIT_DELAY`)
- **Retry:** 3 attempts with exponential backoff via `tenacity` (retries on `RateLimitError`, `APIConnectionError`, `APITimeoutError`)
- **Content truncation:** Content capped at `MAX_CONTENT_LENGTH` (8000 chars)

### Processing Steps Per Item

1. **Content selection** — Pick best content (priority: thread > full > preview > article fields)
2. **Hash check** — Compute SHA-256 of content; skip if unchanged and already processed
3. **Summary generation** — GPT-4o-mini with generic prompt: "Summarize this content in 1-2 sentences, capturing the key insight."
4. **Embedding generation** — Concatenate summary + content → text-embedding-3-small → 1536-dim vector
5. **Vector storage** — Upsert to Supabase pgvector (summary is saved even if Supabase fails)

### Failure Handling

| Failure | Behavior |
|---------|----------|
| Summary generation fails | Both `summary_status` and `embedding_status` set to "failed" |
| Embedding generation fails | Summary is kept; only `embedding_status` set to "failed" |
| Supabase upsert fails | Summary is kept; `embedding_status` set to "failed" |
| Re-ingest of failed item | Processing statuses reset to "pending", auto-retried |
| Missing API key | Ingest blocked entirely with 503 error |

### Smart Reprocess

When `/api/items/{id}/reprocess` is called (without `force=true`), the processor compares the SHA-256 content hash. If content hasn't changed and summary is already completed, processing is skipped.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Extension | Chrome Manifest V3, Vanilla JavaScript |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (file-based) |
| Validation | Pydantic v2 |
| Server | Uvicorn (ASGI) |
| AI / LLM | OpenAI GPT-4o-mini (summaries), text-embedding-3-small (embeddings) |
| Vector DB | Supabase pgvector (HNSW index, cosine similarity) |
| Retry | tenacity (exponential backoff) |
| HTTP Client | httpx (async) |

---

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | SQLite connection string | `sqlite:///./data/neurolink.db` |
| OPENAI_API_KEY | OpenAI API key (**required** for ingest) | `""` |
| OPENAI_EMBEDDING_MODEL | Embedding model name | `text-embedding-3-small` |
| OPENAI_SUMMARY_MODEL | Summary model name | `gpt-4o-mini` |
| SUPABASE_URL | Supabase project URL | `""` |
| SUPABASE_SERVICE_KEY | Supabase service role key | `""` |
| AI_PROCESSING_ENABLED | Enable background processing | `true` |
| MAX_CONTENT_LENGTH | Max content chars sent to OpenAI | `8000` |
| EMBEDDING_DIMENSION | Vector dimension | `1536` |
| RATE_LIMIT_DELAY | Seconds between API calls | `0.5` |

---

## Key Architectural Decisions

### Extension-Based Content Extraction (Not Playwright)

**Original Design (Removed):** Extension sent URLs → Backend used Playwright to fetch content.
**Problem:** Playwright runs unauthenticated browser; Twitter requires login.
**Current Design:** Extension sends URLs + full content → Backend stores and processes.

### Dual Database Strategy (SQLite + Supabase)

**Decision:** Keep SQLite as primary store for structured data, use Supabase only for vector search.
**Rationale:** SQLite is simple, local, no setup. pgvector provides proper HNSW-indexed similarity search that SQLite can't do. If Supabase goes down, summaries are still saved locally.

### Background Processing with Fresh Sessions

**Critical pattern:** Background tasks create their own `SessionLocal()` instead of receiving the request's DB session. The request session is closed after the response is sent, which would cause errors in background tasks.

### Custom JSONType for SQLite

SQLite doesn't have native JSON support. A custom `JSONType` TypeDecorator in `models/item.py` handles serialization/deserialization of the `extra_data` field.

### Incremental Scrolling for Virtual DOM

Twitter virtualizes its bookmark list - only ~6-11 items exist in DOM at any time. Solution: Scroll 800px at a time, capturing items after each scroll before they disappear.

---

## Known Limitations

1. **BackgroundTasks durability** — Lost on server restart. OK for dev, use Celery/Redis for prod.
2. **SQLite concurrency** — Enable WAL mode if "database locked" errors occur.
3. **Embedding dimension** — Hardcoded 1536. Update config + Supabase table if model changes.
4. **No Alembic migrations** — Schema changes require DB deletion and recreation in dev.

---

## Phase Roadmap

### Phase 1: The Collector (Completed)
- [x] Chrome Extension for scraping bookmarks
- [x] FastAPI Backend for storage
- [x] SQLite database
- [x] Content type detection (tweet vs article)
- [x] Metadata extraction (images, quotes, videos)
- [x] "Show more" button expansion
- [x] Virtual scrolling fix (incremental capture)

### Phase 2: The Processor (Completed)
- [x] OpenAI summarization (GPT-4o-mini)
- [x] Embedding generation (text-embedding-3-small)
- [x] Supabase pgvector storage
- [x] Background processing pipeline
- [x] Semantic search with filters
- [x] Smart reprocess (content hash comparison)
- [x] Bulk processing endpoint
- [x] Processing status/stats endpoints

### Phase 3: The Oracle (Future)
- [ ] RAG-based chat interface
- [ ] Multi-turn conversation with knowledge base
- [ ] Advanced search UI
