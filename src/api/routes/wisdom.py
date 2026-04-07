"""Wisdom API routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.wisdom_service import WisdomService
from src.services.embedding_service import get_embedding
from src.api.schemas import (
    WisdomEntryOut, WisdomQuery, SemanticSearchQuery,
    FlourishingScoreRequest, FlourishingScoreResponse,
    TraditionOut, ThemeOut, CrossReferenceOut,
)

router = APIRouter(prefix="/wisdom", tags=["wisdom"])


@router.get("/", response_model=list[WisdomEntryOut])
async def list_wisdom(
    topic: str | None = None,
    tradition: str | None = None,
    theme: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve wisdom entries with optional filters."""
    service = WisdomService(db)
    entries = await service.get_wisdom(
        topic=topic, tradition_slug=tradition, theme_slug=theme,
        limit=limit, offset=offset,
    )
    return entries


@router.post("/search", response_model=list[WisdomEntryOut])
async def semantic_search(
    body: SemanticSearchQuery,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across all wisdom entries."""
    embedding = await get_embedding(body.query)
    service = WisdomService(db)
    entries = await service.semantic_search(embedding, limit=body.limit)
    return entries


@router.get("/{entry_id}", response_model=WisdomEntryOut)
async def get_wisdom_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single wisdom entry by ID."""
    service = WisdomService(db)
    entry = await service.get_entry_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wisdom entry not found")
    return entry


@router.get("/{entry_id}/cross-references", response_model=list[CrossReferenceOut])
async def get_cross_references(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get cross-tradition references for a wisdom entry."""
    service = WisdomService(db)
    refs = await service.get_cross_references(entry_id)
    return refs


@router.get("/perspectives/{topic}", response_model=list[WisdomEntryOut])
async def cross_cultural_perspectives(
    topic: str,
    limit: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Get perspectives on a topic from multiple traditions."""
    service = WisdomService(db)
    entries = await service.get_cross_cultural_perspectives(topic, limit=limit)
    return entries


@router.post("/flourishing-score", response_model=FlourishingScoreResponse)
async def flourishing_score(body: FlourishingScoreRequest, db: AsyncSession = Depends(get_db)):
    """Score text against human flourishing dimensions."""
    service = WisdomService(db)
    scores = await service.flourishing_score(body.text)
    return FlourishingScoreResponse(**scores)


# ---- Traditions & Themes ----

@router.get("/traditions/list", response_model=list[TraditionOut])
async def list_traditions(db: AsyncSession = Depends(get_db)):
    service = WisdomService(db)
    return await service.list_traditions()


@router.get("/themes/list", response_model=list[ThemeOut])
async def list_themes(db: AsyncSession = Depends(get_db)):
    service = WisdomService(db)
    return await service.list_themes()
