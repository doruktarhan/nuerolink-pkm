# Local Development Setup

> **Last Updated:** 2026-02-05
> **Related Docs:** [Architecture](../system/architecture.md) | [Critical Errors](../system/critical-errors.md)

---

## Prerequisites

- Python 3.11+
- Chrome browser
- Git
- OpenAI API key (required for ingest/processing)
- Supabase project (required for vector search)

---

## Backend Setup

### 1. Create virtual environment

```bash
cd neurolink/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in required values:

```env
DATABASE_URL=sqlite:///./data/neurolink.db

# Required - get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here

# Required - get from Supabase project settings > API
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ-your-service-role-key

# Optional overrides (defaults are fine)
AI_PROCESSING_ENABLED=true
OPENAI_SUMMARY_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
MAX_CONTENT_LENGTH=8000
RATE_LIMIT_DELAY=0.5
```

### 4. Set up Supabase vector database

1. Go to your Supabase project dashboard
2. Open **SQL Editor**
3. Run the migration file: `backend/migrations/supabase/001_vector_setup.sql`
   - This creates the `item_embeddings` table, HNSW index, and `match_items()` search function

### 5. Start the server

```bash
cd neurolink/backend
uvicorn app.main:app --reload
```

Server runs at http://localhost:8000

### 6. Verify server is running

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","ai_enabled":true}
```

If `ai_enabled` is `false`, your `OPENAI_API_KEY` is not set correctly.

---

## Extension Setup

### 1. Load extension in Chrome

1. Open Chrome
2. Navigate to `chrome://extensions`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `neurolink/extension/` directory

### 2. Test extension

1. Navigate to https://twitter.com/i/bookmarks
2. Click the NeuroLink extension icon
3. Click "Sync Bookmarks"

---

## Testing the Full Flow

### 1. Manual API test

```bash
# Ingest a test item (requires OPENAI_API_KEY set)
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"items": [{"url": "https://twitter.com/user/status/123", "full_content": "Test content about AI"}]}'

# List items
curl http://localhost:8000/api/items

# Check processing status
curl http://localhost:8000/api/items/1/status

# Get processing stats
curl http://localhost:8000/api/processing/stats

# Run semantic search
curl -X POST http://localhost:8000/api/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "limit": 5}'
```

### 2. Extension test

1. Ensure backend is running
2. Go to Twitter bookmarks page
3. Open extension popup
4. Click "Sync Bookmarks"
5. Check results in popup

### 3. Verify database

```bash
# Using sqlite3
sqlite3 backend/data/neurolink.db "SELECT id, source_url, status, summary_status, embedding_status FROM saved_items;"
```

### 4. Bulk process existing items

```bash
# Process all pending/failed items
curl -X POST http://localhost:8000/api/processing/run-all
```

---

## Troubleshooting

### Backend won't start

- Check Python version: `python --version` (need 3.11+)
- Ensure virtual environment is activated
- Check for port conflicts on 8000

### "AI processing unavailable: OPENAI_API_KEY not configured" (503)

- Ingest now requires `OPENAI_API_KEY` to be set in `.env`
- Check your `.env` file has the key without quotes around the value

### Extension doesn't appear

- Ensure Developer mode is enabled
- Try reloading the extension
- Check Chrome's extension error page

### Extension not responding after reload

**Important:** After reloading the extension in `chrome://extensions`, you must **refresh the Twitter bookmarks page**. The content script is not automatically re-injected into already-open tabs.

### CORS errors

- Ensure backend is running on http://localhost:8000
- Check that CORS middleware is configured in main.py

### Processing stuck / items not getting summarized

1. Check `curl http://localhost:8000/api/processing/stats` to see status counts
2. Check item-level status: `curl http://localhost:8000/api/items/1/status`
3. If items are "failed", check the `processing_error` field
4. Retry with: `curl -X POST http://localhost:8000/api/processing/run-all`

### "database locked" errors

Enable WAL mode on SQLite:
```bash
sqlite3 backend/data/neurolink.db "PRAGMA journal_mode=WAL;"
```

---

## Database Reset

When schema changes are made (new columns added to the model), the SQLite database must be recreated:

```bash
rm backend/data/neurolink.db
# Restart server - tables will be recreated automatically
```

**Note:** This deletes all local data. Supabase embeddings will be orphaned — delete them too if resetting:
```sql
-- Run in Supabase SQL Editor
TRUNCATE item_embeddings;
```

---

## Development Tips

### Hot reload

Backend auto-reloads when files change (with `--reload` flag).

For extension changes:
1. Make changes
2. Go to `chrome://extensions`
3. Click reload button on the extension
4. **Refresh the Twitter page**

### View API docs

FastAPI auto-generates OpenAPI docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Debug extension

1. Open DevTools on Twitter bookmarks page (F12)
2. Go to Console tab
3. Filter by `[NeuroLink]` to see extension logs
4. Run "Sync Bookmarks" and watch console output

### Reprocess a single item

```bash
# Smart reprocess (skips if content unchanged)
curl -X POST http://localhost:8000/api/items/1/reprocess

# Force reprocess
curl -X POST "http://localhost:8000/api/items/1/reprocess?force=true"
```
