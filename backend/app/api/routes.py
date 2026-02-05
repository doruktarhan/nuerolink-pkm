from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from pathlib import Path
import json

from app.core.database import get_db
from app.core.config import settings
from app.models.item import SavedItem
from app.schemas.ingest import (
    IngestPayload,
    IngestResponse,
    SavedItemResponse,
    ItemListResponse,
    ProcessingStatusResponse,
    SemanticSearchRequest,
    SemanticSearchResult,
    SemanticSearchResponse,
    BulkProcessResponse,
    ProcessingStatsResponse
)
from app.services.processor import (
    process_item,
    process_all_pending,
    get_processing_stats
)
from app.services.openai_service import get_openai_service
from app.services.vector_service import get_vector_service

# Debug snapshots storage directory
DEBUG_DIR = Path(__file__).parent.parent.parent / "data" / "debug_snapshots"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


def check_api_key_configured():
    """Check if OpenAI API key is configured."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI processing unavailable: OPENAI_API_KEY not configured"
        )


@router.get("/health")
async def health_check():
    return {"status": "ok", "ai_enabled": bool(settings.OPENAI_API_KEY)}


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest_items(
    payload: IngestPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest items from the extension.
    The extension now provides full content, so we just store it.
    For each item:
    - Check for duplicates
    - Store with full_content from extension
    - Set status based on whether content was provided
    - Trigger background AI processing if API key is configured
    """
    # Block ingest if API key is missing
    check_api_key_configured()

    new_count = 0
    duplicate_count = 0
    failed_count = 0
    items_to_process = []

    for item in payload.items:
        # Extract content_type from metadata
        content_type = "tweet"
        if item.extra_data and "content_type" in item.extra_data:
            content_type = item.extra_data["content_type"]

        # Determine if we have content
        # For articles: title in metadata counts as content
        # For tweets: full_content or preview_text counts
        has_content = item.full_content is not None
        if not has_content and content_type == "article" and item.extra_data:
            has_content = item.extra_data.get("article_title") is not None

        # Check for existing item
        existing = db.execute(
            select(SavedItem).where(SavedItem.source_url == item.url)
        ).scalar_one_or_none()

        if existing:
            if payload.skip_duplicates:
                # Update existing item with new content
                existing.raw_preview = item.preview_text
                existing.full_content = item.full_content
                existing.thread_content = item.thread_content
                existing.content_type = content_type
                existing.extra_data = item.extra_data
                existing.status = "fetched" if has_content else "pending"
                existing.fetch_attempts = 1 if has_content else 0
                # Reset processing status for re-processing
                existing.summary_status = "pending"
                existing.embedding_status = "pending"
                existing.processing_error = None
                if has_content:
                    new_count += 1
                    items_to_process.append(existing.id)
                else:
                    failed_count += 1
            else:
                duplicate_count += 1
            continue

        # Determine status based on whether content was fetched by extension
        status = "fetched" if has_content else "pending"

        # Create new item with content from extension
        saved_item = SavedItem(
            source_url=item.url,
            source_platform=payload.platform,
            content_type=content_type,
            raw_preview=item.preview_text,
            full_content=item.full_content,
            thread_content=item.thread_content,
            extra_data=item.extra_data,
            status=status,
            fetch_attempts=1 if has_content else 0,
            summary_status="pending",
            embedding_status="pending"
        )
        db.add(saved_item)
        db.flush()  # Get the ID

        if has_content:
            new_count += 1
            items_to_process.append(saved_item.id)
        else:
            failed_count += 1

    db.commit()

    # Trigger background processing for all new/updated items
    if settings.AI_PROCESSING_ENABLED and items_to_process:
        for item_id in items_to_process:
            background_tasks.add_task(process_item, item_id)

    success = failed_count == 0
    message = f"Processed {len(payload.items)} items: {new_count} new, {duplicate_count} duplicates, {failed_count} failed"

    return IngestResponse(
        success=success,
        new_count=new_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
        message=message
    )


@router.get("/api/items", response_model=ItemListResponse)
async def list_items(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List saved items with optional status filter."""
    query = select(SavedItem)

    if status:
        query = query.where(SavedItem.status == status)

    query = query.order_by(SavedItem.created_at.desc())
    query = query.offset(offset).limit(limit)

    items = db.execute(query).scalars().all()

    # Get total count
    count_query = select(SavedItem)
    if status:
        count_query = count_query.where(SavedItem.status == status)
    total = len(db.execute(count_query).scalars().all())

    return ItemListResponse(
        items=[SavedItemResponse.model_validate(item) for item in items],
        total=total
    )


@router.get("/api/items/{item_id}", response_model=SavedItemResponse)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single item by ID."""
    item = db.execute(
        select(SavedItem).where(SavedItem.id == item_id)
    ).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return SavedItemResponse.model_validate(item)


@router.get("/api/items/{item_id}/status", response_model=ProcessingStatusResponse)
async def get_item_status(item_id: int, db: Session = Depends(get_db)):
    """Get processing status for a single item."""
    item = db.execute(
        select(SavedItem).where(SavedItem.id == item_id)
    ).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return ProcessingStatusResponse(
        item_id=item.id,
        summary_status=item.summary_status,
        embedding_status=item.embedding_status,
        has_summary=item.summary is not None,
        processing_error=item.processing_error,
        processed_at=item.processed_at,
        content_hash=item.content_hash
    )


@router.post("/api/items/{item_id}/reprocess")
async def reprocess_item(
    item_id: int,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force reprocess even if content unchanged"),
    db: Session = Depends(get_db)
):
    """
    Trigger reprocessing of a single item.
    By default, uses smart reprocess (only if content changed).
    Use force=true to regenerate regardless.
    """
    check_api_key_configured()

    item = db.execute(
        select(SavedItem).where(SavedItem.id == item_id)
    ).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if force:
        # Clear content hash to force reprocess
        item.content_hash = None
        item.summary_status = "pending"
        item.embedding_status = "pending"
        item.processing_error = None
        db.commit()

    background_tasks.add_task(process_item, item_id)

    return {"message": f"Item {item_id} queued for reprocessing", "force": force}


@router.get("/api/processing/stats", response_model=ProcessingStatsResponse)
async def get_stats():
    """Get processing statistics."""
    stats = get_processing_stats()
    return ProcessingStatsResponse(**stats)


@router.post("/api/processing/run-all", response_model=BulkProcessResponse)
async def run_all_processing(background_tasks: BackgroundTasks):
    """
    Bulk process all pending items.
    Runs in background and returns immediately.
    """
    check_api_key_configured()

    background_tasks.add_task(process_all_pending)

    return BulkProcessResponse(
        queued_count=-1,  # Unknown until processing starts
        message="Bulk processing started in background"
    )


@router.post("/api/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search across embedded items.
    Returns items sorted by similarity with optional filters.
    Includes items still being processed with is_processing flag.
    """
    check_api_key_configured()

    openai_service = get_openai_service()
    vector_service = get_vector_service()

    # Generate query embedding
    query_embedding = await openai_service.generate_query_embedding(request.query)

    # Search in Supabase
    matches = vector_service.search_similar(
        query_embedding=query_embedding,
        match_threshold=request.threshold,
        match_count=request.limit,
        content_type=request.content_type,
        after=request.after,
        before=request.before
    )

    # Fetch full items from SQLite
    results = []
    for match in matches:
        item = db.execute(
            select(SavedItem).where(SavedItem.id == match["neurolink_item_id"])
        ).scalar_one_or_none()

        if item:
            results.append(SemanticSearchResult(
                item=SavedItemResponse.model_validate(item),
                similarity=match["similarity"],
                is_processing=item.embedding_status != "completed"
            ))

    return SemanticSearchResponse(
        results=results,
        total=len(results)
    )


# =============================================================================
# DEBUG ENDPOINTS - For AI-assisted debugging
# =============================================================================

@router.post("/api/debug")
async def save_debug_snapshot(snapshot: dict):
    """
    Save a debug snapshot from the extension.
    Returns the snapshot ID for later retrieval.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_id = f"debug_{timestamp}"
    filepath = DEBUG_DIR / f"{snapshot_id}.json"

    # Add server-side metadata
    snapshot["_server_received"] = datetime.now().isoformat()
    snapshot["_id"] = snapshot_id

    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Also save as "latest" for easy access
    latest_path = DEBUG_DIR / "latest.json"
    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    return {
        "success": True,
        "id": snapshot_id,
        "path": str(filepath)
    }


@router.get("/api/debug/latest")
async def get_latest_debug_snapshot():
    """
    Get the most recent debug snapshot.
    Used by AI agents to analyze extension behavior.
    """
    latest_path = DEBUG_DIR / "latest.json"

    if not latest_path.exists():
        raise HTTPException(status_code=404, detail="No debug snapshots found")

    with open(latest_path, "r") as f:
        snapshot = json.load(f)

    return snapshot


@router.get("/api/debug/list")
async def list_debug_snapshots(limit: int = Query(10, ge=1, le=100)):
    """List available debug snapshots."""
    snapshots = []

    for filepath in sorted(DEBUG_DIR.glob("debug_*.json"), reverse=True)[:limit]:
        with open(filepath, "r") as f:
            data = json.load(f)
            snapshots.append({
                "id": data.get("_id", filepath.stem),
                "timestamp": data.get("timestamp"),
                "totalArticles": data.get("totalArticlesFound", 0),
                "captured": data.get("summary", {}).get("captured", 0),
                "skipped": data.get("summary", {}).get("skipped", 0)
            })

    return {"snapshots": snapshots}


@router.get("/api/debug/{snapshot_id}")
async def get_debug_snapshot(snapshot_id: str):
    """Get a specific debug snapshot by ID."""
    filepath = DEBUG_DIR / f"{snapshot_id}.json"

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

    with open(filepath, "r") as f:
        snapshot = json.load(f)

    return snapshot
