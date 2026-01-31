OpenAI Codex v0.88.0 (research preview)
--------
workdir: /Users/doruktarhan/Dev/External/Workshop_App/neurolink
model: gpt-5.2-codex
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: auto
session id: 019c1574-820a-7a01-b827-f20f2e836935
--------
user
# Consultant Task

You are a CONSULTANT. Analyze and recommend, do NOT implement.

## Rules
- You MAY: Read files, grep, search, use MCPs, explore freely
- You MAY NOT: Edit, write, or create any files
- Explore the codebase yourself - do not wait to be spoon-fed

## Mode: planning

## Problem
Chrome extension captures tweets but skips Twitter Articles. We need an intelligent way for AI agents to inspect/debug what the extension sees on the Twitter bookmarks page. 

Key constraints:
1. Playwright does NOT work - Twitter requires authentication and Playwright runs unauthenticated browser
2. Sending raw HTML to AI is inefficient and time-consuming
3. The Claude Chrome extension might be useful
4. Need a systematic way to compare what extension sees vs what gets captured

## Project Location
/Users/doruktarhan/Dev/External/Workshop_App/neurolink

## Project Files
./.agent/README.md
./.agent/sop/local-dev.md
./.agent/system/architecture.md
./.agent/system/critical-errors.md
./backend/app/api/routes.py
./backend/app/models/item.py
./extension/content.js
./extension/manifest.json
./extension/popup.js

## Key Resources to Explore
- `.agent/system/critical-errors.md` - Documents the article skipping issue
- `extension/content.js` - Main scraping logic where the bug likely exists
- `extension/manifest.json` - Extension permissions

## What Has Been Tried
- Raw HTML dumps to AI agent (inefficient, incomplete)
- Playwright for fetching (fails - no auth)
- Console logging (helps but AI cannot see it)

## Deliverable
1. **Understanding**: What you found exploring the extension code
2. **Analysis**: Why current debugging approaches fail
3. **Recommendation**: Intelligent debugging strategy that lets AI agents actually observe extension behavior
4. **Specific Ideas**: Tools, techniques, or architectures to enable AI-assisted debugging
5. **Pitfalls**: What to avoid
6. **Alternatives**: Other approaches considered
mcp startup: no servers

thinking
**Starting file exploration**
Plan update
Need to explore codebase then analyze and recommend without changes.
  → Review agent docs and critical error notes for context
  • Inspect extension code paths (content script, manifest, popup) and backend capture model/routes
  • Synthesize findings and propose AI-friendly debugging strategy with pitfalls/alternatives

thinking
**Preparing to read files**

I'm setting up to read files using shell commands for efficient content retrieval before detailed analysis.
exec
/bin/zsh -lc ls in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 41ms:
README.md
backend
extension

thinking
**Checking for hidden agent files**
exec
/bin/zsh -lc 'ls -a' in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 39ms:
.
..
.agent
.git
.gitignore
README.md
backend
extension

thinking
**Reviewing agent documentation**
exec
/bin/zsh -lc "sed -n '1,200p' .agent/system/critical-errors.md" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 39ms:
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

exec
/bin/zsh -lc "sed -n '200,400p' .agent/system/critical-errors.md" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 43ms:
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


thinking
**Planning inspection of extension and backend files**

I'm prioritizing reviewing extension files and backend code next, with a possible later look at architecture or README docs as needed.
exec
/bin/zsh -lc "sed -n '1,200p' extension/content.js" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 38ms:
const BACKEND_URL = 'http://localhost:8000';

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'scrapeBookmarks') {
    scrapeAndSync(message.batchLimit, message.skipDuplicates)
      .then(sendResponse)
      .catch(err => sendResponse({ error: err.message }));
    return true; // Keep channel open for async response
  }
});

async function scrapeAndSync(batchLimit, skipDuplicates = false) {
  const collectedItems = new Map();
  let lastHeight = 0;
  let noNewContentCount = 0;
  let duplicatesFound = false;

  // Expand all "Show more" buttons before initial scrape
  await expandAllShowMore();
exec
/bin/zsh -lc "sed -n '200,400p' extension/content.js" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 38ms:
    }

    // Extract article title and description
    // They appear in specific divs after the cover image
    const contentArea = article.querySelector('[class*="r-xyw6el"]');
    if (contentArea) {
      const textDivs = contentArea.querySelectorAll('div[dir="auto"]');
      if (textDivs.length >= 1) {
        extra_data.article_title = textDivs[0].innerText;
        fullContent = textDivs[0].innerText;
        previewText = textDivs[0].innerText;
      }
      if (textDivs.length >= 2) {
        extra_data.article_description = textDivs[1].innerText;
        fullContent = `${extra_data.article_title}\n\n${extra_data.article_description}`;
      }
    }

    // Fallback: try to find any prominent text
    if (!fullContent) {

thinking
**Planning manifest and popup**
exec
/bin/zsh -lc 'cat extension/manifest.json' in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 41ms:
{
  "manifest_version": 3,
  "name": "NeuroLink Bookmark Sync",
  "version": "1.0.0",
  "description": "Sync your Twitter bookmarks to NeuroLink",
  "permissions": [
    "activeTab",
    "storage"
  ],
  "host_permissions": [
    "https://twitter.com/*",
    "https://x.com/*",
    "http://localhost:8000/*"
  ],
  "action": {
    "default_popup": "popup.html"
  },
  "content_scripts": [
    {
      "matches": ["https://twitter.com/*", "https://x.com/*"],
exec
/bin/zsh -lc "sed -n '1,200p' extension/popup.js" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 41ms:
const BACKEND_URL = 'http://localhost:8000';

const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const syncBtn = document.getElementById('syncBtn');
const batchLimitInput = document.getElementById('batchLimit');
const resultsEl = document.getElementById('results');
const errorMessageEl = document.getElementById('errorMessage');

// Load saved batch limit
chrome.storage.local.get(['batchLimit'], (result) => {
  if (result.batchLimit) {
    batchLimitInput.value = result.batchLimit;
  }
});

// Save batch limit on change
batchLimitInput.addEventListener('change', () => {
  chrome.storage.local.set({ batchLimit: parseInt(batchLimitInput.value) });
});

thinking
**Exploring backend models and routes**

I'm reviewing the item model and related backend routes to understand data structures and API endpoints for better implementation planning.
exec
/bin/zsh -lc "sed -n '1,200p' backend/app/models/item.py" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 38ms:
from datetime import datetime
import json
from sqlalchemy import String, Text, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class JSONType(TypeDecorator):
    """SQLite-compatible JSON type."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):

thinking
**Noting focus on routes**
exec
/bin/zsh -lc "sed -n '1,240p' backend/app/api/routes.py" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 42ms:
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.item import SavedItem
from app.schemas.ingest import (
    IngestPayload,
    IngestResponse,
    SavedItemResponse,
    ItemListResponse
)

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


thinking
**Checking architecture for context**

I'll quickly review the architecture files to confirm if they contain relevant schema or extra_data details that might help clarify the system context.
exec
/bin/zsh -lc "sed -n '1,200p' .agent/system/architecture.md" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 40ms:
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



thinking
**Analyzing extension article detection limits**

The extension relies on detecting tweets via `/status/` links and article images via specific data attributes, which likely misses Twitter Articles shown differently in bookmarks. Playwright is blocked by auth, and raw HTML captures are too large, so a systematic comparison between what the extension sees and actual page content is needed. Recommendations include AI-assisted inspection tools like Claude's extension and strategies to handle varied HTML structures and authentication challenges when debugging this capture gap.
thinking
**Identifying fragile selectors and logging gaps**

The article detection depends on a fragile auto-generated class and presence of a `/status/` link; missing these causes skips and null content. Console logs aren’t accessible to AI agents, so I’ll recommend instrumentation that forwards structured logs externally or provides a local viewer for real-time debugging. Next, I'll check for any existing debugging guidelines or requirements that could inform these recommendations.
exec
/bin/zsh -lc "sed -n '1,200p' .agent/README.md" in /Users/doruktarhan/Dev/External/Workshop_App/neurolink succeeded in 38ms:
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


thinking
**Updating plan statuses**

I'm noting that step 1 is done and step 2 might be done; I'll update the plan after reviewing critical errors and the extension/back details.
Plan update
Reviewed docs and inspected extension/backend scraping flow.
  ✓ Review agent docs and critical error notes for context
  ✓ Inspect extension code paths (content script, manifest, popup) and backend capture model/routes
  → Synthesize findings and propose AI-friendly debugging strategy with pitfalls/alternatives


thinking
**Proposing structured debug payloads**

Suggest adding a debug mode in the extension that collects minimal subtree snapshots and key extraction data per article, enabling robust backend diagnostics despite dynamic DOM changes and partial virtualization.
thinking
**Detailing debug overlay and snapshot strategy**

Propose an in-extension debug mode that overlays captured vs skipped items with bounding boxes and reasons, gathers minimal JSON summaries per article, and uses DOM "fingerprints" and mutation observers to track dynamic changes. Suggest building paired views for "seen" versus "sent" items with skip reasons and counts, plus a debug pipeline to systematically compare extraction outcomes, enhancing visibility into misses and classification errors.
Plan update
Prepared analysis and recommendations based on inspected code and docs.
  ✓ Review agent docs and critical error notes for context
  ✓ Inspect extension code paths (content script, manifest, popup) and backend capture model/routes
  ✓ Synthesize findings and propose AI-friendly debugging strategy with pitfalls/alternatives


thinking
**Summarizing brittle tweet detection logic**

I analyzed that content.js relies on selectors like `article[data-testid="tweet"]` and status URL patterns involving `/status/` extracted via regex, plus brittle class pattern matches like `article-cover-image` and `class*="r-xyw6el"`. Early returns skip articles missing status links or with username 'i', which happens for internal URLs like `/i/status/123` or `/i/web/status/123`. The regex patterns misinterpret these, causing skips even if tweets exist, revealing fragility in the item detection approach.
thinking
**Proposing intelligent debugging strategy**

Understanding:  
- content.js relies on `/status/` links and brittle selectors like `article-cover-image` (in `content.js`) plus class patterns, causing many articles to be skipped if they lack these exact markers.  
- Regex parsing misinterprets internal URLs like `/i/web/status/123`, producing invalid usernames/URLs and thus skipping items incorrectly.  
- The extension logs skips only via console, inaccessible to AI, so debugging lacks systematic records or visibility beyond local logs.  
- Virtualization and dynamic class names make raw HTML snapshots or selector-based debugging ineffective.  

Analysis:  
- Current debugging is minimal and local, missing many failure cases due to reliance on single indicators (`/status/` links, brittle testids).  
- Article detection fails when bookmarks have different URL patterns or omit expected cover image markers.  
- Regex parsing and duplicate filtering based on malformed URLs cause both false skips and duplicate drops.  
- AI analysis is hindered by lack of structured debug info, heavy HTML, and dynamic page state.  

Recommendation and Specific Ideas:  
- Add a toggleable debug mode that collects per-article diagnostic data, including element index, bounding rect, content type signals, anchor hrefs, data-testid attributes, truncated text preview, and explicit skip reasons.  
- Collect lightweight snapshots: sanitized outerHTML (attributes only, truncated text), selector fingerprints (path, data-testid, roles, CSS class hash), and small cropped screenshots of each article using `getBoundingClientRect` and `chrome.tabs.captureVisibleTab`.  
- Provide a UI panel or popup within the extension showing detected articles, their skip reasons, and what was actually sent to backend to compare.  
- Implement a debug endpoint for posting JSON debug payloads from the extension for remote inspection by AI agents.  
- Offer a “bookmark inspector” mode with in-page overlays labeling detected articles with content types and skip reasons, plus a “Copy debug report” button for diagnostics sharing.  
- Use a two-tier debugging approach: Level 1 for summary counts and DOM signatures; Level 2 for deep capture (HTML snippets, images) of problematic items, enabling focused AI inspection.  
- Suggest using the Claude Chrome extension’s element inspection and summarizing tools in manual workflows to complement automated debug data without full automation.  

Pitfalls:  
- Avoid capturing sensitive user data or excessive full HTML to respect privacy and performance.  
- Beware ephemeral dynamic classes and virtualization that can cause inconsistent snapshots.  
- Avoid overloading extension or UI with debug data that harms user experience or slows page.  
- Ensure throttling and limits on debug capture during infinite scroll.  

Alternatives:  
- Use Chrome DevTools Protocol or Puppeteer connecting to existing Chrome user profiles (with persistence) for external scripted inspection, though complexity and auth challenges exist.  
- Manual export of Twitter bookmarks or archive as data source for offline analysis.  
- Incorporate persistent debug sessions with run IDs to correlate multi-step investigations.  

This
thinking
**Summarizing extension scraping and debug limits**

The extension extracts tweets/articles using fragile selectors and skips items lacking `/status/` links, explaining many "articles skipped" cases; Playwright debucodex
**Understanding**
- The extension scrapes only `article[data-testid="tweet"]` elements and then **requires** a link matching `a[href*="/status/"]` plus a strict `/username/status/id` regex; if that fails, the item is skipped early and never reaches content extraction. `extension/content.js`
- Article detection relies on `data-testid="article-cover-image"` and a class substring `r-xyw6el` for title/description; both look fragile because those classes are generated and can vary. `extension/content.js`
- The skip rules include `username === 'i'`; internal URLs like `/i/article/...` or `/i/...` will be skipped even if they acodex
**Understanding**
- The scrape path is entirely in the content script: `extension/content.js` finds `article[data-testid="tweet"]`, pulls the first `a[href*="/status/"]`, regexes `/username/status/id`, then calls `extractContentFromArticle`. Anything without that status link is skipped before content-type detection.
- Article detection is based on `data-testid="article-cover-image"` and then brittle selectors like `[class*="r-xyw6el"]` and `span[class*="r-bcqeeo"]` for title/description. If those don’t match, `content_type` remains `"tweet"` and text can be null.
- Only console logs capture “what happened”; nothing structured is persisted or sent to the backend. Backend (`backend/app/api/routes.py`) just stores what it’s given and defaults `content_type` to `"tweet"` when missing.
- There’s no artifact to compare “elements seen on the page” vs “items ingested and stored.”

**Analysis (why current debugging fails)**
- Playwright is unauthenticated, so it can’t see the bookmarks DOM at all (already documented in `.agent/system/critical-errors.md`).
- Raw HTML dumps are huge and still don’t answer *why* a given element was skipped (no reason codes, no mapping to the scraper’s decisions).
- Console logs are invisible to AI and not persisted; they’re also unstructured (no stable ID for an element).
- Likely skip mechanism: anything lacking `/status/` links is dropped. If Twitter Articles use `/i/article/...` or other link patterns, they’re currently discarded as “No status link found.” That explains “articles skipped.”
- Likely misclassification mechanism: `data-testid="article-cover-image"` or the class-based text selectors don’t match the current DOM, so even captured articles remain labeled `"tweet"`.

**Recommendation (intelligent, AI-observable debugging)**
Build a **debug mode** that exports a compact, structured “DOM audit report” from the authenticated page, instead of raw HTML. It should record, for each candidate element, exactly what the scraper saw and why it did or didn’t ingest it. That gives AI a reliable, small artifact to inspect.

Key outcomes:
- You can compare **candidates vs ingested** and identify missing articles or misclassified content types.
- You can tell if the failure is link detection, content extraction, or DOM structure drift.
- AI gets a structured JSON + optional screenshot, not a megabyte HTML blob.

**Specific ideas (tools/techniques/architecture)**
- **Reason-coded per-element report**: for each `article` element, record
  - `element_index`, `found_links` (first N `href`s), `status_link_found`, `status_regex_match`, `detected_content_type`, `title/description`, `fullContent`, `skip_reason`.
  - `dom_signature`: list of `data-testid` values found, `role`/`aria-label` snippets, a short CSS path to the primary link.
- **Diff report**: compare (a) URLs/IDs found on the page vs (b) items ingested and stored; output missing URLs and content_type mismatches.
- **Screenshot mapping**: capture a page screenshot and include per-element bounding boxes + index labels in the JSON; AI can visually confirm which element corresponds to which report entry.
- **Optional CDP snapshot**: using `chrome.debugger` to grab `Accessibility.getFullAXTree` or `DOMSnapshot.captureSnapshot` for a structured DOM that’s smaller and more semantic than HTML.
- **UI for debugging**: a “Debug Run” button in the popup that outputs the JSON (copy to clipboard or POST to a local `/api/debug` endpoint).

**Pitfalls**
- Avoid fragile class fragments like `r-xyw6el` / `r-bcqeeo`; they churn frequently.
- Don’t rely on console logs alone; they’re not AI-visible and are hard to correlate.
- Don’t ship full `outerHTML` for every element; it’s noisy and too large.
- Don’t assume `/status/` links exist for every bookmark (articles may use `/i/article/` or other patterns).
- Be mindful of privacy: keep debug artifacts local and gated behind an explicit toggle.

**Alternatives**
- Attach Puppeteer/Playwright to an **existing authenticated Chrome profile** via remote debugging. This gives a full DOM to AI tools but is more invasive and setup-heavy.
- Manual DevTools inspection + selective copy/paste of a problematic element (low effort, low repeatability).
- Use X/Twitter data export as an external ground truth for URLs, then compare with ingested items (slow, not real‑time).

If you want, I can draft a concrete debug-report JSON schema and a repeatable “debug run” checklist for your team—still analysis-only, no code changes.
tokens used
39,632
**Understanding**
- The scrape path is entirely in the content script: `extension/content.js` finds `article[data-testid="tweet"]`, pulls the first `a[href*="/status/"]`, regexes `/username/status/id`, then calls `extractContentFromArticle`. Anything without that status link is skipped before content-type detection.
- Article detection is based on `data-testid="article-cover-image"` and then brittle selectors like `[class*="r-xyw6el"]` and `span[class*="r-bcqeeo"]` for title/description. If those don’t match, `content_type` remains `"tweet"` and text can be null.
- Only console logs capture “what happened”; nothing structured is persisted or sent to the backend. Backend (`backend/app/api/routes.py`) just stores what it’s given and defaults `content_type` to `"tweet"` when missing.
- There’s no artifact to compare “elements seen on the page” vs “items ingested and stored.”

**Analysis (why current debugging fails)**
- Playwright is unauthenticated, so it can’t see the bookmarks DOM at all (already documented in `.agent/system/critical-errors.md`).
- Raw HTML dumps are huge and still don’t answer *why* a given element was skipped (no reason codes, no mapping to the scraper’s decisions).
- Console logs are invisible to AI and not persisted; they’re also unstructured (no stable ID for an element).
- Likely skip mechanism: anything lacking `/status/` links is dropped. If Twitter Articles use `/i/article/...` or other link patterns, they’re currently discarded as “No status link found.” That explains “articles skipped.”
- Likely misclassification mechanism: `data-testid="article-cover-image"` or the class-based text selectors don’t match the current DOM, so even captured articles remain labeled `"tweet"`.

**Recommendation (intelligent, AI-observable debugging)**
Build a **debug mode** that exports a compact, structured “DOM audit report” from the authenticated page, instead of raw HTML. It should record, for each candidate element, exactly what the scraper saw and why it did or didn’t ingest it. That gives AI a reliable, small artifact to inspect.

Key outcomes:
- You can compare **candidates vs ingested** and identify missing articles or misclassified content types.
- You can tell if the failure is link detection, content extraction, or DOM structure drift.
- AI gets a structured JSON + optional screenshot, not a megabyte HTML blob.

**Specific ideas (tools/techniques/architecture)**
- **Reason-coded per-element report**: for each `article` element, record
  - `element_index`, `found_links` (first N `href`s), `status_link_found`, `status_regex_match`, `detected_content_type`, `title/description`, `fullContent`, `skip_reason`.
  - `dom_signature`: list of `data-testid` values found, `role`/`aria-label` snippets, a short CSS path to the primary link.
- **Diff report**: compare (a) URLs/IDs found on the page vs (b) items ingested and stored; output missing URLs and content_type mismatches.
- **Screenshot mapping**: capture a page screenshot and include per-element bounding boxes + index labels in the JSON; AI can visually confirm which element corresponds to which report entry.
- **Optional CDP snapshot**: using `chrome.debugger` to grab `Accessibility.getFullAXTree` or `DOMSnapshot.captureSnapshot` for a structured DOM that’s smaller and more semantic than HTML.
- **UI for debugging**: a “Debug Run” button in the popup that outputs the JSON (copy to clipboard or POST to a local `/api/debug` endpoint).

**Pitfalls**
- Avoid fragile class fragments like `r-xyw6el` / `r-bcqeeo`; they churn frequently.
- Don’t rely on console logs alone; they’re not AI-visible and are hard to correlate.
- Don’t ship full `outerHTML` for every element; it’s noisy and too large.
- Don’t assume `/status/` links exist for every bookmark (articles may use `/i/article/` or other patterns).
- Be mindful of privacy: keep debug artifacts local and gated behind an explicit toggle.

**Alternatives**
- Attach Puppeteer/Playwright to an **existing authenticated Chrome profile** via remote debugging. This gives a full DOM to AI tools but is more invasive and setup-heavy.
- Manual DevTools inspection + selective copy/paste of a problematic element (low effort, low repeatability).
- Use X/Twitter data export as an external ground truth for URLs, then compare with ingested items (slow, not real‑time).

If you want, I can draft a concrete debug-report JSON schema and a repeatable “debug run” checklist for your team—still analysis-only, no code changes.
mal “diff report” format that keeps data tiny but actionable.
