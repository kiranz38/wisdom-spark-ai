"""Models for tracking crawler activity."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.wisdom import Base


class CrawlRun(Base):
    """Record of a single crawler execution cycle."""
    __tablename__ = "crawl_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running, completed, failed

    # Stats
    candidates_discovered: Mapped[int] = mapped_column(Integer, default=0)
    candidates_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    candidates_approved: Mapped[int] = mapped_column(Integer, default=0)
    candidates_rejected: Mapped[int] = mapped_column(Integer, default=0)
    candidates_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    entries_ingested: Mapped[int] = mapped_column(Integer, default=0)

    # Sources used
    sources_used: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Error info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class CrawlCandidate(Base):
    """Record of each discovered candidate and its evaluation result."""
    __tablename__ = "crawl_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crawl_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Source info
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawl_source: Mapped[str] = mapped_column(String(64), nullable=False)

    # Evaluation result
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending, approved, rejected_quality, rejected_divisive, rejected_duplicate, error
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # If approved and ingested, link to the entry
    wisdom_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
