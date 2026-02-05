import asyncio
import hashlib
from datetime import datetime
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.item import SavedItem
from app.services.openai_service import OpenAIService
from app.services.vector_service import VectorService


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


def get_best_content(item: SavedItem) -> str | None:
    """
    Get the best available content for processing.
    Priority: thread_content -> full_content -> raw_preview -> article fields
    """
    if item.thread_content:
        return item.thread_content
    if item.full_content:
        return item.full_content
    if item.raw_preview:
        return item.raw_preview
    if item.extra_data:
        # Try article fields
        title = item.extra_data.get("article_title", "")
        description = item.extra_data.get("article_description", "")
        if title or description:
            return f"{title}\n{description}".strip()
    return None


async def process_item(item_id: int) -> dict:
    """
    Process a single item: generate summary and embedding.
    Creates fresh database session for background task safety.

    Returns dict with processing results.
    """
    openai_service = OpenAIService()
    vector_service = VectorService()

    with SessionLocal() as db:
        item = db.get(SavedItem, item_id)
        if not item:
            return {"success": False, "error": "Item not found"}

        content = get_best_content(item)
        if not content:
            item.summary_status = "failed"
            item.embedding_status = "failed"
            item.processing_error = "No content available for processing"
            db.commit()
            return {"success": False, "error": "No content available"}

        content_hash = compute_content_hash(content)

        # Check if content has changed (smart reprocess)
        if item.content_hash == content_hash and item.summary_status == "completed":
            # Content unchanged and already processed
            return {"success": True, "skipped": True, "reason": "Content unchanged"}

        item.content_hash = content_hash
        item.summary_status = "processing"
        item.embedding_status = "processing"
        item.processing_error = None
        db.commit()

        summary = None
        embedding_id = None

        # Step 1: Generate summary
        try:
            summary = await openai_service.generate_summary(content)
            item.summary = summary
            item.summary_model = settings.OPENAI_SUMMARY_MODEL
            item.summary_status = "completed"
            db.commit()
        except Exception as e:
            item.summary_status = "failed"
            item.processing_error = f"Summary generation failed: {str(e)}"
            item.embedding_status = "failed"
            db.commit()
            return {"success": False, "error": str(e), "stage": "summary"}

        # Step 2: Generate embedding (even if Supabase fails, we keep the summary)
        try:
            embedding = await openai_service.generate_embedding_for_item(summary, content)

            # Step 3: Store in Supabase
            try:
                embedding_id = vector_service.upsert_embedding(
                    neurolink_item_id=item.id,
                    source_url=item.source_url,
                    content_type=item.content_type,
                    content=content,
                    embedding=embedding
                )
                item.embedding_id = embedding_id
                item.embedding_status = "completed"
            except Exception as e:
                # Supabase failed, but we still have the summary
                item.embedding_status = "failed"
                item.processing_error = f"Supabase upsert failed: {str(e)}"

        except Exception as e:
            item.embedding_status = "failed"
            if item.processing_error:
                item.processing_error += f"; Embedding generation failed: {str(e)}"
            else:
                item.processing_error = f"Embedding generation failed: {str(e)}"

        item.processed_at = datetime.utcnow()
        db.commit()

        return {
            "success": item.summary_status == "completed",
            "summary_status": item.summary_status,
            "embedding_status": item.embedding_status,
            "embedding_id": embedding_id
        }


async def process_all_pending() -> dict:
    """
    Process all items with pending or failed status.
    Returns stats about the processing run.
    """
    processed = 0
    failed = 0
    skipped = 0

    with SessionLocal() as db:
        # Get all items that need processing
        query = select(SavedItem).where(
            (SavedItem.summary_status.in_(["pending", "failed"])) |
            (SavedItem.embedding_status.in_(["pending", "failed"]))
        )
        items = db.execute(query).scalars().all()
        item_ids = [item.id for item in items]

    for item_id in item_ids:
        result = await process_item(item_id)
        if result.get("skipped"):
            skipped += 1
        elif result.get("success"):
            processed += 1
        else:
            failed += 1

        # Rate limiting between items
        await asyncio.sleep(settings.RATE_LIMIT_DELAY)

    return {
        "total": len(item_ids),
        "processed": processed,
        "failed": failed,
        "skipped": skipped
    }


def reset_failed_items() -> int:
    """
    Reset failed items to pending status for retry on next sync.
    Returns count of reset items.
    """
    with SessionLocal() as db:
        query = select(SavedItem).where(
            (SavedItem.summary_status == "failed") |
            (SavedItem.embedding_status == "failed")
        )
        items = db.execute(query).scalars().all()

        count = 0
        for item in items:
            if item.summary_status == "failed":
                item.summary_status = "pending"
            if item.embedding_status == "failed":
                item.embedding_status = "pending"
            item.processing_error = None
            count += 1

        db.commit()
        return count


def get_processing_stats() -> dict:
    """Get processing statistics."""
    with SessionLocal() as db:
        total = db.execute(select(SavedItem)).scalars().all()

        summary_stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        embedding_stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }

        for item in total:
            if item.summary_status in summary_stats:
                summary_stats[item.summary_status] += 1
            if item.embedding_status in embedding_stats:
                embedding_stats[item.embedding_status] += 1

        return {
            "total_items": len(total),
            "summary": summary_stats,
            "embedding": embedding_stats
        }
