from pydantic import BaseModel
from datetime import datetime
from typing import Any


class IngestItem(BaseModel):
    url: str
    preview_text: str | None = None
    full_content: str | None = None
    thread_content: str | None = None
    extra_data: dict[str, Any] | None = None


class IngestPayload(BaseModel):
    items: list[IngestItem]
    platform: str = "twitter"
    skip_duplicates: bool = False


class IngestResponse(BaseModel):
    success: bool
    new_count: int
    duplicate_count: int
    failed_count: int
    message: str


class SavedItemResponse(BaseModel):
    id: int
    source_url: str
    source_platform: str
    content_type: str | None
    raw_preview: str | None
    full_content: str | None
    thread_content: str | None
    extra_data: dict[str, Any] | None
    status: str
    fetch_attempts: int
    created_at: datetime
    updated_at: datetime
    # AI Processing fields
    summary: str | None = None
    summary_model: str | None = None
    summary_status: str = "pending"
    embedding_status: str = "pending"
    embedding_id: int | None = None
    processing_error: str | None = None
    processed_at: datetime | None = None
    content_hash: str | None = None

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    items: list[SavedItemResponse]
    total: int


class ProcessingStatusResponse(BaseModel):
    item_id: int
    summary_status: str
    embedding_status: str
    has_summary: bool
    processing_error: str | None
    processed_at: datetime | None
    content_hash: str | None


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    threshold: float = 0.7
    content_type: str | None = None
    after: datetime | None = None
    before: datetime | None = None


class SemanticSearchResult(BaseModel):
    item: SavedItemResponse
    similarity: float
    is_processing: bool


class SemanticSearchResponse(BaseModel):
    results: list[SemanticSearchResult]
    total: int


class BulkProcessResponse(BaseModel):
    queued_count: int
    message: str


class ProcessingStatsResponse(BaseModel):
    total_items: int
    summary: dict[str, int]
    embedding: dict[str, int]
