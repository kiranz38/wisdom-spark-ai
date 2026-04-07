"""
Seed the database with the initial wisdom corpus from YAML files.

Usage:
    python -m scripts.seed_corpus
"""

import asyncio
import uuid
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings
from src.models.wisdom import Base, Tradition, Theme, WisdomEntry, WisdomTheme, CrossReference

CORPUS_DIR = Path(__file__).parent.parent / "src" / "corpus"
TRADITIONS_DIR = CORPUS_DIR / "traditions"
THEMES_DIR = CORPUS_DIR / "themes"
CROSS_REFS_FILE = CORPUS_DIR / "cross_references.yaml"


async def seed_themes(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Load universal themes and return slug->id mapping."""
    themes_file = THEMES_DIR / "universal_themes.yaml"
    data = yaml.safe_load(themes_file.read_text())

    theme_map = {}
    for t in data["themes"]:
        existing = await session.execute(
            select(Theme).where(Theme.slug == t["slug"])
        )
        theme = existing.scalar_one_or_none()
        if theme:
            theme_map[t["slug"]] = theme.id
            print(f"  Theme '{t['slug']}' already exists, skipping")
            continue

        theme = Theme(
            id=uuid.uuid4(),
            slug=t["slug"],
            name=t["name"],
            description=t["description"].strip(),
            anti_patterns=t.get("anti_patterns"),
        )
        session.add(theme)
        theme_map[t["slug"]] = theme.id
        print(f"  + Theme: {t['name']}")

    await session.flush()
    return theme_map


async def seed_tradition(session: AsyncSession, filepath: Path, theme_map: dict[str, uuid.UUID]):
    """Load a tradition YAML file and seed entries."""
    data = yaml.safe_load(filepath.read_text())
    trad_data = data["tradition"]

    # Upsert tradition
    existing = await session.execute(
        select(Tradition).where(Tradition.slug == trad_data["slug"])
    )
    tradition = existing.scalar_one_or_none()
    if not tradition:
        tradition = Tradition(
            id=uuid.uuid4(),
            slug=trad_data["slug"],
            name=trad_data["name"],
            origin_region=trad_data.get("origin_region"),
            era=trad_data.get("era"),
            description=trad_data["description"].strip(),
            key_figures=trad_data.get("key_figures"),
            core_principles=trad_data.get("core_principles"),
        )
        session.add(tradition)
        await session.flush()
        print(f"\n+ Tradition: {trad_data['name']}")
    else:
        print(f"\n  Tradition '{trad_data['name']}' exists, adding new entries only")

    # Seed entries
    entries = data.get("entries", [])
    for entry_data in entries:
        # Check for duplicate by source_text prefix
        prefix = entry_data["source_text"].strip()[:100]
        existing_entry = await session.execute(
            select(WisdomEntry).where(
                WisdomEntry.tradition_id == tradition.id,
                WisdomEntry.source_text.startswith(prefix),
            )
        )
        if existing_entry.scalar_one_or_none():
            print(f"    Entry already exists: {prefix[:50]}...")
            continue

        entry = WisdomEntry(
            id=uuid.uuid4(),
            tradition_id=tradition.id,
            source_text=entry_data["source_text"].strip(),
            source_author=entry_data.get("source_author"),
            source_work=entry_data.get("source_work"),
            source_era=entry_data.get("source_era"),
            original_language=entry_data.get("original_language"),
            core_principle=entry_data["core_principle"].strip(),
            practical_application=entry_data["practical_application"].strip(),
            modern_context=entry_data.get("modern_context", "").strip() or None,
            addresses_anti_patterns=entry_data.get("addresses_anti_patterns"),
            reduces_suffering=entry_data.get("reduces_suffering", 0.0),
            respects_dignity=entry_data.get("respects_dignity", 0.0),
            promotes_cooperation=entry_data.get("promotes_cooperation", 0.0),
            considers_future=entry_data.get("considers_future", 0.0),
            honors_nature=entry_data.get("honors_nature", 0.0),
            citation=entry_data.get("citation"),
            verified=True,
        )
        session.add(entry)
        await session.flush()

        # Link themes
        for theme_slug in entry_data.get("themes", []):
            if theme_slug in theme_map:
                wt = WisdomTheme(wisdom_id=entry.id, theme_id=theme_map[theme_slug])
                session.add(wt)

        print(f"    + {entry_data.get('source_author', 'Unknown')}: {prefix[:60]}...")

    await session.flush()


async def seed_cross_references(session: AsyncSession):
    """Load cross-tradition references from YAML."""
    data = yaml.safe_load(CROSS_REFS_FILE.read_text())

    for ref in data.get("cross_references", []):
        # Find source entry
        source_trad = await session.execute(
            select(Tradition).where(Tradition.slug == ref["source_tradition"])
        )
        source_tradition = source_trad.scalar_one_or_none()
        if not source_tradition:
            print(f"    Skipping: tradition '{ref['source_tradition']}' not found")
            continue

        source_entry_result = await session.execute(
            select(WisdomEntry).where(
                WisdomEntry.tradition_id == source_tradition.id,
                WisdomEntry.source_text.startswith(ref["source_prefix"][:80]),
            )
        )
        source_entry = source_entry_result.scalar_one_or_none()

        # Find target entry
        target_trad = await session.execute(
            select(Tradition).where(Tradition.slug == ref["target_tradition"])
        )
        target_tradition = target_trad.scalar_one_or_none()
        if not target_tradition:
            print(f"    Skipping: tradition '{ref['target_tradition']}' not found")
            continue

        target_entry_result = await session.execute(
            select(WisdomEntry).where(
                WisdomEntry.tradition_id == target_tradition.id,
                WisdomEntry.source_text.startswith(ref["target_prefix"][:80]),
            )
        )
        target_entry = target_entry_result.scalar_one_or_none()

        if not source_entry or not target_entry:
            print(f"    Skipping cross-ref: could not match entries for {ref['source_tradition']} -> {ref['target_tradition']}")
            continue

        # Check for existing
        existing = await session.execute(
            select(CrossReference).where(
                CrossReference.source_id == source_entry.id,
                CrossReference.target_id == target_entry.id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        cross_ref = CrossReference(
            id=uuid.uuid4(),
            source_id=source_entry.id,
            target_id=target_entry.id,
            relationship_type=ref["relationship_type"],
            explanation=ref["explanation"].strip(),
            similarity_score=ref.get("similarity_score", 0.0),
        )
        session.add(cross_ref)
        print(f"    + {ref['source_tradition']} <-> {ref['target_tradition']}: {ref['relationship_type']}")

    await session.flush()


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    # Enable pgvector extension and create tables
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/verified.")

    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        # Seed themes
        print("\nSeeding universal themes...")
        theme_map = await seed_themes(session)

        # Seed each tradition
        print("\nSeeding traditions and wisdom entries...")
        for filepath in sorted(TRADITIONS_DIR.glob("*.yaml")):
            await seed_tradition(session, filepath, theme_map)

        # Seed cross-references
        if CROSS_REFS_FILE.exists():
            print("\nSeeding cross-references...")
            await seed_cross_references(session)

        await session.commit()
        print("\nSeed complete!")

        # Summary
        from sqlalchemy import func
        count = await session.execute(select(func.count(WisdomEntry.id)))
        total = count.scalar()
        trad_count = await session.execute(select(func.count(Tradition.id)))
        total_trads = trad_count.scalar()
        theme_count = await session.execute(select(func.count(Theme.id)))
        total_themes = theme_count.scalar()
        print(f"\nCorpus: {total} wisdom entries across {total_trads} traditions and {total_themes} universal themes")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
