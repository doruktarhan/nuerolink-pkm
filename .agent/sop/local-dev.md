# Local Development Setup

> **Last Updated:** 2026-01-31
> **Related Docs:** [Architecture](../system/architecture.md) | [Critical Errors](../system/critical-errors.md)

---

## Prerequisites

- Python 3.11+
- Chrome browser
- Git

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

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env if you need custom database path
```

### 4. Start the server

```bash
cd neurolink/backend
uvicorn app.main:app --reload
```

Server runs at http://localhost:8000

### 5. Verify server is running

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

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
# Ingest a test item
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"items": [{"url": "https://twitter.com/user/status/123", "preview_text": "test"}]}'

# List items
curl http://localhost:8000/api/items
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
sqlite3 backend/data/neurolink.db "SELECT id, source_url, status FROM saved_items;"
```

---

## Troubleshooting

### Backend won't start

- Check Python version: `python --version` (need 3.11+)
- Ensure virtual environment is activated
- Check for port conflicts on 8000

### Extension doesn't appear

- Ensure Developer mode is enabled
- Try reloading the extension
- Check Chrome's extension error page

### Extension not responding after reload

**Important:** After reloading the extension in `chrome://extensions`, you must **refresh the Twitter bookmarks page**. The content script is not automatically re-injected into already-open tabs.

### CORS errors

- Ensure backend is running on http://localhost:8000
- Check that CORS middleware is configured in main.py

---

## Development Tips

### Hot reload

Backend auto-reloads when files change (with `--reload` flag).

For extension changes:
1. Make changes
2. Go to `chrome://extensions`
3. Click reload button on the extension
4. **Refresh the Twitter page**

### Database reset

```bash
rm backend/data/neurolink.db
# Restart server - tables will be recreated
```

### View API docs

FastAPI auto-generates OpenAPI docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Debug extension

1. Open DevTools on Twitter bookmarks page (F12)
2. Go to Console tab
3. Filter by `[NeuroLink]` to see extension logs
4. Run "Sync Bookmarks" and watch console output
