# NeuroLink Architecture

> **Last Updated:** 2026-01-31
> **Related Docs:** [README](../README.md) | [Critical Errors](critical-errors.md) | [Local Dev Setup](../sop/local-dev.md)

---

## Overview

NeuroLink is a Personal Knowledge Management (PKM) system that:
1. **Collects** Twitter/X bookmarks via Chrome extension (authenticated session)
2. **Processes** content (extracts text, metadata, detects content types)
3. **Stores** in SQLite database with rich metadata
4. **(Future)** Enriches with AI summaries and embeddings
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
- **Purpose:** API server for data ingestion and retrieval
- **Key Files:**
  - `app/main.py` - FastAPI application with CORS configuration
  - `app/api/routes.py` - API endpoints (`/api/ingest`, `/api/items`)
  - `app/models/item.py` - SQLAlchemy ORM models with custom JSONType
  - `app/schemas/ingest.py` - Pydantic validation schemas
  - `app/core/database.py` - SQLAlchemy engine and session management
  - `app/core/config.py` - Environment configuration

### 3. SQLite Database
- **Location:** `backend/data/neurolink.db`
- **Purpose:** Persistent storage for saved items with full metadata

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                                │
│  ┌─────────────────┐                                                │
│  │ Chrome Extension│──── Scrapes bookmarks page ────────────────┐   │
│  │ (content.js)    │     (authenticated session)                │   │
│  └─────────────────┘                                            │   │
└─────────────────────────────────────────────────────────────────│───┘
                                                                  │
                                                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND SERVER                                │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │ FastAPI         │────▶│ Routes          │────▶│ SQLite DB     │ │
│  │ (localhost:8000)│     │ /api/ingest     │     │ neurolink.db  │ │
│  └─────────────────┘     │ /api/items      │     └───────────────┘ │
│                          └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
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
6. Backend checks for duplicates, stores new items
7. Items stored with status "fetched" (content provided) or "pending"

**IMPORTANT:** Twitter uses virtual scrolling - only ~6-11 items exist in DOM at once. Items are removed from DOM when scrolled out of view. The incremental capture strategy ensures items are captured before they disappear.

---

## Database Schema

### `saved_items` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| source_url | VARCHAR(2048) | Unique tweet URL (indexed) |
| source_platform | VARCHAR(50) | "twitter" (for future multi-platform support) |
| content_type | VARCHAR(50) | "tweet" or "article" |
| raw_preview | TEXT | Preview text from extension |
| full_content | TEXT | Full tweet/article text |
| thread_content | TEXT | Thread context (Phase 2 feature) |
| extra_data | JSON/TEXT | Metadata object (custom JSONType) |
| status | VARCHAR(20) | "pending", "fetched", "fetch_failed" |
| fetch_attempts | INTEGER | Retry counter |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

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

---

## API Endpoints

| Method | Path | Description | Parameters |
|--------|------|-------------|------------|
| GET | `/health` | Health check | - |
| POST | `/api/ingest` | Ingest items from extension | Body: `IngestPayload` |
| GET | `/api/items` | List saved items | `?status=`, `?limit=` (1-200), `?offset=` |
| GET | `/api/items/{id}` | Get single item by ID | - |

### IngestPayload Schema
```python
{
  "items": [
    {
      "url": str,                    # Required
      "preview_text": str | None,
      "full_content": str | None,
      "thread_content": str | None,
      "extra_data": dict | None
    }
  ],
  "platform": str = "twitter",
  "skip_duplicates": bool = False
}
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Extension | Chrome Manifest V3, Vanilla JavaScript |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (file-based) |
| Validation | Pydantic v2 |
| Server | Uvicorn (ASGI) |

---

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | SQLite connection string | `sqlite:///./data/neurolink.db` |

**Note:** Playwright configuration was removed. Content is now fetched directly by the extension.

---

## Key Architectural Decisions

### Extension-Based Content Extraction (Not Playwright)

**Original Design (Removed):**
```
Extension (URLs only) → Backend → Playwright (fetch content)
```
**Problem:** Playwright runs unauthenticated browser; Twitter requires login.

**Current Design:**
```
Extension (URLs + full content) → Backend (store only)
```
**Benefits:** Simpler, faster, no auth issues, leverages user's authenticated session.

### Custom JSONType for SQLite

SQLite doesn't have native JSON support. A custom `JSONType` TypeDecorator in `models/item.py` handles serialization/deserialization of the `extra_data` field.

### Incremental Scrolling for Virtual DOM

Twitter virtualizes its bookmark list - only ~6-11 items exist in DOM at any time. Original approach scrolled to bottom instantly, losing top items.

**Solution:** Scroll 800px at a time, capturing items after each scroll before they disappear.

```javascript
// OLD (broken): window.scrollTo(0, document.body.scrollHeight);
// NEW (working):
currentScrollY += 800;
window.scrollTo(0, currentScrollY);
await sleep(800);
scrapeVisibleTweets(collectedItems); // Capture immediately
```

### Debug Telemetry Tools

Built-in debugging for diagnosing capture issues:

| Tool | Purpose |
|------|---------|
| Debug Snapshot | Captures current DOM state - shows what extension sees |
| Debug Mode Sync | Runs full sync while tracking every item encountered |
| Backend `/api/debug` | Stores debug reports for post-mortem analysis |

---

## Future Phases

### Phase 2: The Processor
- Image downloading and local storage
- Video metadata extraction
- External link fetching (article content)
- OpenAI summarization
- Embedding generation

### Phase 3: The Oracle
- Vector storage (Pinecone/Chroma)
- RAG-based chat interface
- Semantic search across all saved content
