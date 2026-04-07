"""Crawler monitoring API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.crawl_log import CrawlRun, CrawlCandidate
from src.models.wisdom import WisdomEntry

router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.get("/stats")
async def crawler_stats(db: AsyncSession = Depends(get_db)):
    """Get overall crawler statistics."""
    # Total entries
    total_entries = await db.execute(select(func.count(WisdomEntry.id)))
    # Auto-crawled (unverified) entries
    auto_entries = await db.execute(
        select(func.count(WisdomEntry.id)).where(WisdomEntry.verified == False)
    )
    # Human-curated (verified) entries
    verified_entries = await db.execute(
        select(func.count(WisdomEntry.id)).where(WisdomEntry.verified == True)
    )
    # Total crawl runs
    total_runs = await db.execute(select(func.count(CrawlRun.id)))
    # Total ingested by crawler
    total_ingested = await db.execute(
        select(func.sum(CrawlRun.entries_ingested))
    )

    return {
        "corpus": {
            "total_entries": total_entries.scalar() or 0,
            "auto_crawled": auto_entries.scalar() or 0,
            "human_curated": verified_entries.scalar() or 0,
        },
        "crawler": {
            "total_runs": total_runs.scalar() or 0,
            "total_ingested": total_ingested.scalar() or 0,
        },
    }


@router.get("/runs")
async def recent_runs(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get recent crawl runs."""
    result = await db.execute(
        select(CrawlRun)
        .order_by(desc(CrawlRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "discovered": r.candidates_discovered,
            "evaluated": r.candidates_evaluated,
            "approved": r.candidates_approved,
            "rejected": r.candidates_rejected,
            "duplicates": r.candidates_duplicate,
            "ingested": r.entries_ingested,
            "sources": r.sources_used,
            "error": r.error_message,
        }
        for r in runs
    ]
