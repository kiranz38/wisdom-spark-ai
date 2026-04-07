import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, ForeignKey, DateTime,
    Table, UniqueConstraint, Index, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# --- Association Tables ---

class WisdomTheme(Base):
    """Many-to-many: wisdom entries <-> themes."""
    __tablename__ = "wisdom_themes"

    wisdom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wisdom_entries.id", ondelete="CASCADE"), primary_key=True
    )
    theme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True
    )


# --- Core Models ---

class Tradition(Base):
    """A philosophical, spiritual, or cultural tradition."""
    __tablename__ = "traditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    origin_region: Mapped[str] = mapped_column(String(128), nullable=True)
    era: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    key_figures: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["Marcus Aurelius", "Epictetus"]
    core_principles: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    entries: Mapped[list["WisdomEntry"]] = relationship(back_populates="tradition", lazy="selectin")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Theme(Base):
    """Universal themes that span traditions (compassion, non-harm, dignity, etc.)."""
    __tablename__ = "themes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    anti_patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["tribalism", "dehumanization", "environmental destruction"]

    # Relationships
    entries: Mapped[list["WisdomEntry"]] = relationship(
        secondary="wisdom_themes", back_populates="themes", lazy="selectin"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WisdomEntry(Base):
    """A single piece of curated wisdom — a quote, teaching, principle, or practice."""
    __tablename__ = "wisdom_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source
    tradition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("traditions.id"), nullable=False
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_work: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_era: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    translation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted wisdom
    core_principle: Mapped[str] = mapped_column(Text, nullable=False)
    practical_application: Mapped[str] = mapped_column(Text, nullable=False)
    modern_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Anti-patterns this wisdom addresses
    addresses_anti_patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["hatred based on ethnicity", "environmental neglect", "ego-driven conflict"]

    # Flourishing dimensions (0.0–1.0 scores for how strongly it relates)
    reduces_suffering: Mapped[float] = mapped_column(Float, default=0.0)
    respects_dignity: Mapped[float] = mapped_column(Float, default=0.0)
    promotes_cooperation: Mapped[float] = mapped_column(Float, default=0.0)
    considers_future: Mapped[float] = mapped_column(Float, default=0.0)
    honors_nature: Mapped[float] = mapped_column(Float, default=0.0)

    # Embedding for semantic search
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)

    # Metadata
    verified: Mapped[bool] = mapped_column(default=False)
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tradition: Mapped["Tradition"] = relationship(back_populates="entries", lazy="selectin")
    themes: Mapped[list["Theme"]] = relationship(
        secondary="wisdom_themes", back_populates="entries", lazy="selectin"
    )
    cross_references_from: Mapped[list["CrossReference"]] = relationship(
        foreign_keys="CrossReference.source_id", back_populates="source", lazy="selectin"
    )
    cross_references_to: Mapped[list["CrossReference"]] = relationship(
        foreign_keys="CrossReference.target_id", back_populates="target", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_wisdom_embedding", "embedding", postgresql_using="ivfflat"),
    )


class CrossReference(Base):
    """Links wisdom entries across traditions that share similar insights."""
    __tablename__ = "cross_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wisdom_entries.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wisdom_entries.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. "parallel_insight", "complementary", "deepens", "contrasts"
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)

    source: Mapped["WisdomEntry"] = relationship(foreign_keys=[source_id], back_populates="cross_references_from")
    target: Mapped["WisdomEntry"] = relationship(foreign_keys=[target_id], back_populates="cross_references_to")

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", name="uq_cross_ref"),
    )
