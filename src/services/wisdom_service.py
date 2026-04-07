"""Core service for querying and scoring wisdom entries."""

from uuid import UUID
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector

from src.models.wisdom import WisdomEntry, Tradition, Theme, CrossReference


class WisdomService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Retrieval ----

    async def get_wisdom(
        self,
        topic: str | None = None,
        tradition_slug: str | None = None,
        theme_slug: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[WisdomEntry]:
        """Retrieve wisdom entries with optional filters."""
        stmt = select(WisdomEntry)

        if tradition_slug:
            stmt = stmt.join(Tradition).where(Tradition.slug == tradition_slug)

        if theme_slug:
            stmt = stmt.join(WisdomEntry.themes).where(Theme.slug == theme_slug)

        if topic:
            pattern = f"%{topic}%"
            stmt = stmt.where(
                or_(
                    WisdomEntry.core_principle.ilike(pattern),
                    WisdomEntry.source_text.ilike(pattern),
                    WisdomEntry.practical_application.ilike(pattern),
                    WisdomEntry.modern_context.ilike(pattern),
                )
            )

        stmt = stmt.order_by(WisdomEntry.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def semantic_search(self, embedding: list[float], limit: int = 10) -> list[WisdomEntry]:
        """Find wisdom entries most similar to the given embedding vector."""
        stmt = (
            select(WisdomEntry)
            .where(WisdomEntry.embedding.isnot(None))
            .order_by(WisdomEntry.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_entry_by_id(self, entry_id: UUID) -> WisdomEntry | None:
        result = await self.db.execute(
            select(WisdomEntry).where(WisdomEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    # ---- Cross-tradition ----

    async def get_cross_cultural_perspectives(self, topic: str, limit: int = 10) -> list[dict]:
        """Get wisdom on a topic from as many different traditions as possible."""
        entries = await self.get_wisdom(topic=topic, limit=50)

        # Group by tradition, take top entry from each
        seen_traditions = set()
        results = []
        for entry in entries:
            if entry.tradition_id not in seen_traditions:
                seen_traditions.add(entry.tradition_id)
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    async def find_common_ground(self, theme_slug: str) -> list[dict]:
        """Find entries from different traditions that converge on the same theme."""
        stmt = (
            select(WisdomEntry)
            .join(WisdomEntry.themes)
            .where(Theme.slug == theme_slug)
            .order_by(func.random())
            .limit(20)
        )
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())

        # Group by tradition
        by_tradition = {}
        for entry in entries:
            trad_name = entry.tradition.name if entry.tradition else "Unknown"
            if trad_name not in by_tradition:
                by_tradition[trad_name] = entry
        return by_tradition

    # ---- Scoring ----

    async def flourishing_score(self, text: str) -> dict:
        """Score text against flourishing dimensions using keyword heuristics.
        For v0.1 — will be replaced by ML model in v0.2.
        """
        text_lower = text.lower()

        # Positive signals
        positive_signals = {
            "reduces_suffering": [
                "compassion", "empathy", "help", "heal", "care", "kindness",
                "mercy", "forgive", "support", "comfort", "relieve", "alleviate",
            ],
            "respects_dignity": [
                "dignity", "respect", "equal", "rights", "honor", "worth",
                "autonomy", "consent", "freedom", "justice", "fair",
            ],
            "promotes_cooperation": [
                "together", "cooperat", "collaborat", "community", "unity",
                "harmony", "peace", "dialogue", "bridge", "share", "mutual",
            ],
            "considers_future": [
                "future", "generation", "sustain", "long-term", "legacy",
                "children", "preserve", "steward", "foresight", "tomorrow",
            ],
            "honors_nature": [
                "nature", "earth", "environment", "ecology", "planet",
                "green", "biodiversity", "conservation", "wildlife", "ocean",
            ],
        }

        # Negative signals (divisive / harmful)
        negative_signals = [
            "hate", "inferior", "superior race", "destroy", "eliminate",
            "subhuman", "vermin", "exterminate", "crusade against", "cleanse",
            "they deserve", "those people", "not one of us",
        ]

        scores = {}
        for dimension, keywords in positive_signals.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            scores[dimension] = min(round(hits / max(len(keywords) * 0.3, 1), 2), 1.0)

        # Check for negative signals
        negative_hits = sum(1 for kw in negative_signals if kw in text_lower)
        scores["divisiveness_flag"] = negative_hits > 0
        scores["negative_signal_count"] = negative_hits

        # Overall flourishing score (weighted average)
        dimension_scores = [v for k, v in scores.items() if k in positive_signals]
        scores["overall"] = round(sum(dimension_scores) / len(dimension_scores), 2) if dimension_scores else 0.0

        return scores

    # ---- Traditions & Themes ----

    async def list_traditions(self) -> list[Tradition]:
        result = await self.db.execute(select(Tradition).order_by(Tradition.name))
        return list(result.scalars().all())

    async def list_themes(self) -> list[Theme]:
        result = await self.db.execute(select(Theme).order_by(Theme.name))
        return list(result.scalars().all())

    async def get_cross_references(self, entry_id: UUID) -> list[CrossReference]:
        stmt = select(CrossReference).where(
            or_(CrossReference.source_id == entry_id, CrossReference.target_id == entry_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
