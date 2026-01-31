# NeuroLink Agent Documentation

> **Last Updated:** 2026-01-31
> **Current Phase:** Phase 1 - The Collector (In Progress)
> **Status:** Functional with known issues

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [System Architecture](system/architecture.md) | System overview, components, data flow, database schema, tech stack |
| [Critical Errors & Fixes](system/critical-errors.md) | Known issues, errors encountered, and solutions |
| [Local Development Setup](sop/local-dev.md) | How to set up and run the project locally |

---

## Project Overview

**NeuroLink** is a Personal Knowledge Management (PKM) system that:
1. **Collects** Twitter/X bookmarks via Chrome extension
2. **Processes** content (extracts text, metadata, detects content types)
3. **Stores** in SQLite database
4. **(Future)** Enriches with AI summaries and embeddings
5. **(Future)** Provides RAG-based chat interface

---

## Current Architecture

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

**Key Design:** Content is extracted directly by the Chrome extension using the user's authenticated browser session. No backend fetching required.

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
│   │   ├── api/routes.py     # API endpoints
│   │   ├── models/item.py    # SQLAlchemy models
│   │   ├── schemas/ingest.py # Pydantic schemas
│   │   └── core/
│   │       ├── config.py     # Settings
│   │       └── database.py   # DB connection
│   ├── data/                 # SQLite database location
│   └── requirements.txt
│
└── .agent/                    # Documentation
    ├── README.md             # This file
    ├── system/               # Architecture docs
    │   ├── architecture.md   # Full system design
    │   └── critical-errors.md# Error history & fixes
    └── sop/                  # Standard operating procedures
        └── local-dev.md      # Development setup guide
```

---

## Database Schema (Current)

### `saved_items` table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| source_url | VARCHAR(2048) | Unique tweet URL (indexed) |
| source_platform | VARCHAR(50) | "twitter" |
| content_type | VARCHAR(50) | "tweet" or "article" |
| raw_preview | TEXT | Preview text from extension |
| full_content | TEXT | Full tweet/article text |
| thread_content | TEXT | Thread context (Phase 2) |
| extra_data | JSON/TEXT | Metadata object |
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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/ingest` | Ingest items from extension |
| GET | `/api/items` | List saved items (supports `?status=`, `?limit=`, `?offset=`) |
| GET | `/api/items/{id}` | Get single item by ID |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Extension | Chrome Manifest V3, Vanilla JS |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite |
| API Validation | Pydantic v2 |

---

## Phase Roadmap

### Phase 1: The Collector (Current - In Progress)
- [x] Chrome Extension for scraping bookmarks
- [x] FastAPI Backend for storage
- [x] SQLite database
- [x] Content type detection (tweet vs article)
- [x] Metadata extraction (images, quotes, videos)
- [x] "Show more" button expansion
- [ ] **ISSUE:** Some articles being skipped (see critical-errors.md)
- [ ] Thread extraction

### Phase 2: The Processor (Future)
- [ ] Image downloading and storage
- [ ] Video metadata/transcription
- [ ] External link fetching
- [ ] Full article content extraction
- [ ] OpenAI summarization
- [ ] Embedding generation

### Phase 3: The Oracle (Future)
- [ ] Vector storage (Pinecone/Chroma)
- [ ] RAG-based chat interface
- [ ] Semantic search

---

## Quick Start

```bash
# 1. Start backend
cd neurolink/backend
source venv/bin/activate
uvicorn app.main:app --reload

# 2. Load extension
# Go to chrome://extensions
# Enable Developer mode
# Load unpacked -> select neurolink/extension/

# 3. Use
# Go to twitter.com/i/bookmarks
# Click extension icon -> Sync Bookmarks

# 4. Verify
curl http://localhost:8000/api/items | python -m json.tool
```

---

## Key Files to Understand

1. **`extension/content.js`** - Main scraping logic, content type detection, metadata extraction
2. **`backend/app/api/routes.py`** - API endpoints, ingest logic
3. **`backend/app/models/item.py`** - Database model with JSONType for extra_data
4. **`backend/app/core/database.py`** - SQLAlchemy setup with absolute path handling

---

## For Next Agent

**Priority Issues to Fix:**
1. Articles sometimes not being captured (check console logs for `[NeuroLink]` messages)
2. Extension needs page refresh after reload (content script injection timing)

**See:** [Critical Errors & Fixes](system/critical-errors.md) for detailed error history and solutions.
