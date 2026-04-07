"""
Ingestion pipeline — deduplicates and inserts evaluated wisdom into the database.

Flow:
1. Check for near-duplicates using text similarity + embeddings
2. Match to existing tradition or create "pending" tradition
3. Link to existing themes
4. Generate embedding vector
5. Insert into database
6. Log the crawl event
"""

import uuid
import logging
from datetime import datetime

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.wisdom import WisdomEntry, Tradition, Theme, WisdomTheme
from src.crawler.pipeline.evaluator import EvaluatedWisdom
from src.services.embedding_service import get_embedding

logger = logging.getLogger("wisdom_crawler")


class WisdomIngestor:
    """Deduplicates and inserts evaluated wisdom into the database."""

    def __init__(self, db: AsyncSession, dedup_threshold: float = 0.92):
        self.db = db
        self.dedup_threshold = dedup_threshold
        self._tradition_cache: dict[str, uuid.UUID] = {}
        self._theme_cache: dict[str, uuid.UUID] = {}

    async def ingest(self, wisdom: EvaluatedWisdom) -> WisdomEntry | None:
        """Ingest a single evaluated wisdom entry. Returns entry if inserted, None if duplicate."""

        # Step 1: Check text-based dedup (cheap)
        if await self._is_text_duplicate(wisdom.source_text):
            logger.info(f"Skipped (text duplicate): {wisdom.source_text[:60]}...")
            return None

        # Step 2: Generate embedding
        embedding_text = f"{wisdom.source_text}\n{wisdom.core_principle}\n{wisdom.practical_application}"
        try:
            embedding = await get_embedding(embedding_text)
        except Exception as e:
            logger.warning(f"Embedding generation failed, inserting without: {e}")
            embedding = None

        # Step 3: Check semantic dedup (more expensive but catches paraphrases)
        if embedding and await self._is_semantic_duplicate(embedding):
            logger.info(f"Skipped (semantic duplicate): {wisdom.source_text[:60]}...")
            return None

        # Step 4: Resolve tradition
        tradition_id = await self._resolve_tradition(wisdom.tradition_slug)
        if not tradition_id:
            logger.warning(f"Unknown tradition '{wisdom.tradition_slug}', skipping")
            return None

        # Step 5: Create entry
        entry = WisdomEntry(
            id=uuid.uuid4(),
            tradition_id=tradition_id,
            source_text=wisdom.source_text,
            source_author=wisdom.source_author,
            source_work=wisdom.source_work,
            source_era=wisdom.source_era,
            original_language=wisdom.original_language,
            core_principle=wisdom.core_principle,
            practical_application=wisdom.practical_application,
            modern_context=wisdom.modern_context,
            addresses_anti_patterns=wisdom.addresses_anti_patterns,
            reduces_suffering=wisdom.flourishing_scores.get("reduces_suffering", 0.0),
            respects_dignity=wisdom.flourishing_scores.get("respects_dignity", 0.0),
            promotes_cooperation=wisdom.flourishing_scores.get("promotes_cooperation", 0.0),
            considers_future=wisdom.flourishing_scores.get("considers_future", 0.0),
            honors_nature=wisdom.flourishing_scores.get("honors_nature", 0.0),
            embedding=embedding,
            verified=False,  # Auto-crawled entries start unverified
            citation=wisdom.citation,
        )
        self.db.add(entry)
        await self.db.flush()

        # Step 6: Link themes
        for theme_slug in wisdom.themes:
            theme_id = await self._resolve_theme(theme_slug)
            if theme_id:
                wt = WisdomTheme(wisdom_id=entry.id, theme_id=theme_id)
                self.db.add(wt)

        await self.db.flush()
        logger.info(f"Ingested: [{wisdom.tradition_slug}] {wisdom.source_text[:60]}...")
        return entry

    async def ingest_batch(self, wisdoms: list[EvaluatedWisdom]) -> list[WisdomEntry]:
        """Ingest a batch of evaluated wisdom entries."""
        entries = []
        for wisdom in wisdoms:
            entry = await self.ingest(wisdom)
            if entry:
                entries.append(entry)

        if entries:
            await self.db.commit()
            logger.info(f"Committed {len(entries)} new wisdom entries")
        return entries

    async def _is_text_duplicate(self, source_text: str) -> bool:
        """Check if very similar text already exists (cheap string match)."""
        # Check prefix match (catches exact and near-exact duplicates)
        prefix = source_text.strip()[:100]
        result = await self.db.execute(
            select(func.count(WisdomEntry.id)).where(
                WisdomEntry.source_text.startswith(prefix)
            )
        )
        count = result.scalar()
        return count > 0

    async def _is_semantic_duplicate(self, embedding: list[float]) -> bool:
        """Check if semantically similar entry already exists using cosine distance."""
        try:
            result = await self.db.execute(
                select(WisdomEntry.id)
                .where(WisdomEntry.embedding.isnot(None))
                .order_by(WisdomEntry.embedding.cosine_distance(embedding))
                .limit(1)
            )
            closest = result.scalar_one_or_none()
            if closest is None:
                return False  # No entries with embeddings yet

            # Get the actual distance
            dist_result = await self.db.execute(
                select(WisdomEntry.embedding.cosine_distance(embedding))
                .where(WisdomEntry.id == closest)
            )
            distance = dist_result.scalar()
            similarity = 1 - (distance or 0)
            return similarity >= self.dedup_threshold
        except Exception as e:
            logger.warning(f"Semantic dedup check failed: {e}")
            return False

    async def _resolve_tradition(self, slug: str) -> uuid.UUID | None:
        """Get tradition ID by slug, using cache."""
        if slug in self._tradition_cache:
            return self._tradition_cache[slug]

        result = await self.db.execute(
            select(Tradition).where(Tradition.slug == slug)
        )
        tradition = result.scalar_one_or_none()
        if tradition:
            self._tradition_cache[slug] = tradition.id
            return tradition.id
        return None

    async def _resolve_theme(self, slug: str) -> uuid.UUID | None:
        """Get theme ID by slug, using cache."""
        if slug in self._theme_cache:
            return self._theme_cache[slug]

        result = await self.db.execute(
            select(Theme).where(Theme.slug == slug)
        )
        theme = result.scalar_one_or_none()
        if theme:
            self._theme_cache[slug] = theme.id
            return theme.id
        return None
