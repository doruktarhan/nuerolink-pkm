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

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    items: list[SavedItemResponse]
    total: int
