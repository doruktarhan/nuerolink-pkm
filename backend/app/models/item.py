from datetime import datetime
import json
from sqlalchemy import String, Text, Integer, BigInteger, DateTime, Index
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
        if value is not None:
            return json.loads(value)
        return None


class SavedItem(Base):
    __tablename__ = "saved_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    source_platform: Mapped[str] = mapped_column(String(50), default="twitter")
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="tweet")
    raw_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    fetch_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # AI Processing fields
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary_status: Mapped[str] = mapped_column(String(20), default="pending")
    embedding_status: Mapped[str] = mapped_column(String(20), default="pending")
    embedding_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_saved_items_status", "status"),
        Index("ix_saved_items_summary_status", "summary_status"),
        Index("ix_saved_items_embedding_status", "embedding_status"),
    )
