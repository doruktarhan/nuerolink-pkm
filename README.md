# NeuroLink

Personal Knowledge Management system that ingests Twitter bookmarks for AI enrichment.

## Features

- Chrome extension to scrape Twitter bookmarks
- FastAPI backend for storage and retrieval
- Playwright-based content fetching for full tweet text and threads
- SQLite database for persistence

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn app.main:app --reload
```

### 2. Extension

1. Open `chrome://extensions`
2. Enable Developer mode
3. Load unpacked → select `extension/` folder
4. Navigate to twitter.com/i/bookmarks
5. Click extension → Sync Bookmarks

## Project Structure

```
neurolink/
├── backend/           # FastAPI server
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── core/      # Config, database
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   └── data/          # SQLite database
├── extension/         # Chrome extension
└── .agent/            # Documentation
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/ingest` - Ingest bookmarks
- `GET /api/items` - List saved items
- `GET /api/items/{id}` - Get single item

## Documentation

See [.agent/README.md](.agent/README.md) for detailed documentation.
