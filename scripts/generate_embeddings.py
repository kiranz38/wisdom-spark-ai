"""
Generate embeddings for all wisdom entries that don't have them yet.

Usage:
    python -m scripts.generate_embeddings
"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings
from src.models.wisdom import WisdomEntry
from src.services.embedding_service import get_embeddings_batch

BATCH_SIZE = 20


def build_embedding_text(entry: WisdomEntry) -> str:
    """Combine entry fields into a single text for embedding."""
    parts = [
        entry.source_text,
        f"Core principle: {entry.core_principle}",
        f"Practical application: {entry.practical_application}",
    ]
    if entry.modern_context:
        parts.append(f"Modern context: {entry.modern_context}")
    if entry.addresses_anti_patterns:
        parts.append(f"Addresses: {', '.join(entry.addresses_anti_patterns)}")
    return "\n\n".join(parts)


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        # Count entries without embeddings
        count_result = await session.execute(
            select(func.count(WisdomEntry.id)).where(WisdomEntry.embedding.is_(None))
        )
        total = count_result.scalar()
        print(f"Found {total} entries without embeddings")

        if total == 0:
            print("Nothing to do!")
            return

        # Process in batches
        offset = 0
        processed = 0
        while offset < total:
            result = await session.execute(
                select(WisdomEntry)
                .where(WisdomEntry.embedding.is_(None))
                .offset(0)  # Always 0 since we update as we go
                .limit(BATCH_SIZE)
            )
            entries = list(result.scalars().all())
            if not entries:
                break

            texts = [build_embedding_text(e) for e in entries]
            embeddings = await get_embeddings_batch(texts)

            for entry, emb in zip(entries, embeddings):
                entry.embedding = emb

            await session.commit()
            processed += len(entries)
            print(f"  Embedded {processed}/{total} entries")
            offset += BATCH_SIZE

        print(f"\nDone! Generated embeddings for {processed} entries.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
