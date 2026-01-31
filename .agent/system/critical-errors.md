# Critical Errors & Fixes

> **Last Updated:** 2026-01-31
> **Purpose:** Document errors encountered during development and their solutions for future reference.
> **Related Docs:** [README](../README.md) | [Architecture](architecture.md) | [Local Dev Setup](../sop/local-dev.md)

---

## Table of Contents

1. [SQLAlchemy Reserved Attribute Name](#1-sqlalchemy-reserved-attribute-name)
2. [Database Schema Migration](#2-database-schema-migration)
3. [SQLite Read-Only Database](#3-sqlite-read-only-database)
4. [Content Script Not Loaded](#4-content-script-not-loaded)
5. [Twitter SPA - Fetch Returns Empty HTML](#5-twitter-spa---fetch-returns-empty-html)
6. [Playwright Authentication Issue](#6-playwright-authentication-issue)
7. [Articles Being Skipped](#7-articles-being-skipped-open-issue)

---

## 1. SQLAlchemy Reserved Attribute Name

### Error
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

### Cause
Used `metadata` as a column name in SQLAlchemy model. This conflicts with SQLAlchemy's internal `metadata` attribute.

### Solution
Rename the column from `metadata` to `extra_data` in:
- `backend/app/models/item.py`
- `backend/app/schemas/ingest.py`
- `backend/app/api/routes.py`
- `extension/content.js`

### Prevention
Never use these reserved names for SQLAlchemy model attributes:
- `metadata`
- `registry`
- `__table__`
- `__mapper__`

---

## 2. Database Schema Migration

### Error
```
sqlite3.OperationalError: no such column: saved_items.content_type
```

### Cause
Added new columns (`content_type`, `extra_data`) to the model but SQLite database still has old schema.

### Solution
Delete the database file and restart the server:
```bash
rm neurolink/backend/data/neurolink.db
uvicorn app.main:app --reload
```

### Prevention
For production, use Alembic migrations. For development:
- Document schema changes clearly
- Provide migration instructions
- Consider adding a version check

### Note
This is a **one-time operation** when schema changes. SQLAlchemy's `create_all()` will recreate tables with new schema.

---

## 3. SQLite Read-Only Database

### Error
```
sqlite3.OperationalError: attempt to write a readonly database
```

### Cause
The relative path `sqlite:///./data/neurolink.db` resolved incorrectly depending on where uvicorn was started.

### Solution
Changed `backend/app/core/database.py` to use absolute path:
```python
from pathlib import Path

# Ensure data directory exists
data_dir = Path(__file__).parent.parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Use absolute path for SQLite
db_path = data_dir / "neurolink.db"
database_url = f"sqlite:///{db_path}"
```

### Prevention
Always use absolute paths for SQLite in production configurations.

---

## 4. Content Script Not Loaded

### Error
```
Error: Could not establish connection. Receiving end does not exist.
```

### Cause
After reloading the Chrome extension, the content script is not automatically re-injected into already-open Twitter tabs.

### Solution
**User must refresh the Twitter bookmarks page** after reloading the extension.

### Alternative Fix (Not Implemented)
Add `scripting` permission to manifest.json and programmatically inject content script:
```javascript
// In popup.js
await chrome.scripting.executeScript({
  target: { tabId: tab.id },
  files: ['content.js']
});
```

### Prevention
Document this behavior clearly for users. Consider implementing programmatic injection for better UX.

---

## 5. Twitter SPA - Fetch Returns Empty HTML

### Error
Content fetched via `fetch(url)` returns empty/minimal HTML without tweet content.

### Cause
Twitter/X is a Single Page Application (SPA). When you `fetch()` a URL:
- Server returns a minimal HTML shell
- Content is loaded via JavaScript
- JavaScript doesn't execute in a simple fetch

### Solution
**Removed Playwright fetch approach.** Now scrape content directly from the visible bookmarks page where content is already rendered.

The extension now:
1. Scrapes content from the visible DOM (authenticated session)
2. Clicks "Show more" buttons to expand truncated text
3. Sends complete content to backend

### Related
See [Architecture Changes](#playwright-authentication-issue) below.

---

## 6. Playwright Authentication Issue

### Error
Playwright opens a separate browser without Twitter authentication, causing all content fetches to fail.

### Cause
The original architecture used Playwright on the backend to fetch tweet content. But Playwright runs a separate browser instance that doesn't have the user's Twitter session.

### Solution
**Removed Playwright entirely.** Changed architecture:

**Before (Broken):**
```
Extension (URLs only) → Backend → Playwright (no auth) ❌
```

**After (Working):**
```
Extension (URLs + content) → Backend (store only) ✓
```

### Files Changed
- Removed `playwright>=1.40.0` from `requirements.txt`
- Removed Playwright config from `.env.example` and `config.py`
- Updated `routes.py` to just store (no fetch)
- Updated `content.js` to extract full content

---

## 7. Articles Being Skipped (OPEN ISSUE)

### Status
**Unresolved** - Needs investigation

### Symptom
Some Twitter Articles are not being captured in the database. All items show `content_type: "tweet"` even when articles exist in bookmarks.

### Suspected Causes
1. Article URL extraction may be failing (different link structure?)
2. Article content extraction returning null (selector issue?)
3. Articles may be rendered differently in the DOM

### Debug Steps Added
Console logging was added to `content.js`:
```javascript
console.log(`[NeuroLink] Found ${articles.length} articles on page`);
console.log(`[NeuroLink] Article ${index}: No status link found`);
console.log(`[NeuroLink] Article ${index}: Collected ${contentData.extra_data.content_type} - ${fullUrl}`);
```

### To Investigate
1. Refresh Twitter bookmarks page
2. Open DevTools → Console
3. Run "Sync Bookmarks"
4. Check console output for skipped articles
5. Compare HTML structure of skipped articles vs captured tweets

### Potential Fix
May need to update the URL extraction logic in `scrapeVisibleTweets()` to handle article-specific link structures.

---

## Error Prevention Checklist

When making changes:

- [ ] Test with fresh database (delete .db file)
- [ ] Reload extension AND refresh Twitter page
- [ ] Check browser console for errors
- [ ] Check uvicorn terminal for backend errors
- [ ] Verify API response with `curl http://localhost:8000/api/items`
- [ ] Check all content types (tweets, articles, quotes, images)

---

*Last updated: 2026-01-31*
