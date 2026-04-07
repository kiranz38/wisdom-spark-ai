"""
Wisdom Spark AI — MCP Server

Exposes humanity's philosophical wisdom as tools any AI agent can use.
10 tools spanning retrieval, ethical scoring, reframing, and cross-tradition dialogue.
"""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings
from src.models.wisdom import WisdomEntry, Tradition, Theme, CrossReference, Base
from src.services.wisdom_service import WisdomService

settings = get_settings()

mcp = FastMCP(
    "Wisdom Spark AI",
    description=(
        "Access the distilled wisdom of humanity's greatest philosophical traditions. "
        "Stoicism, Buddhism, Vedanta, Ubuntu, Taoism, Confucianism, and more — "
        "structured for AI consumption to promote human flourishing and ethical reasoning."
    ),
)

# Database session for MCP tools
_engine = create_async_engine(settings.database_url, pool_size=5)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _get_service() -> tuple[WisdomService, AsyncSession]:
    session = _session_factory()
    return WisdomService(session), session


def _entry_to_dict(entry: WisdomEntry) -> dict:
    return {
        "id": str(entry.id),
        "source_text": entry.source_text,
        "source_author": entry.source_author,
        "source_work": entry.source_work,
        "tradition": entry.tradition.name if entry.tradition else None,
        "core_principle": entry.core_principle,
        "practical_application": entry.practical_application,
        "modern_context": entry.modern_context,
        "themes": [t.name for t in entry.themes] if entry.themes else [],
        "flourishing_scores": {
            "reduces_suffering": entry.reduces_suffering,
            "respects_dignity": entry.respects_dignity,
            "promotes_cooperation": entry.promotes_cooperation,
            "considers_future": entry.considers_future,
            "honors_nature": entry.honors_nature,
        },
    }


# ---- Tool 1: Get Wisdom ----

@mcp.tool()
async def get_wisdom(
    topic: str | None = None,
    tradition: str | None = None,
    theme: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Retrieve curated wisdom from humanity's philosophical traditions.

    Args:
        topic: Search topic (e.g. "compassion", "dealing with anger", "environmental stewardship")
        tradition: Filter by tradition slug (stoicism, buddhism, vedanta, ubuntu, taoism, confucianism)
        theme: Filter by universal theme slug (compassion, non-harm, dignity, stewardship, cooperation, golden-rule)
        limit: Number of entries to return (1-20)
    """
    service, session = await _get_service()
    try:
        entries = await service.get_wisdom(
            topic=topic, tradition_slug=tradition, theme_slug=theme,
            limit=min(limit, 20),
        )
        return [_entry_to_dict(e) for e in entries]
    finally:
        await session.close()


# ---- Tool 2: Check Ethical Alignment ----

@mcp.tool()
async def check_ethical_alignment(text: str) -> dict:
    """Evaluate text against human flourishing dimensions.

    Scores the input across 5 dimensions: reduces_suffering, respects_dignity,
    promotes_cooperation, considers_future, honors_nature.
    Also flags divisive or dehumanizing language.

    Args:
        text: The text to evaluate (a statement, decision, policy, etc.)
    """
    service, session = await _get_service()
    try:
        scores = await service.flourishing_score(text)
        guidance = []
        if scores.get("divisiveness_flag"):
            guidance.append(
                "This text contains language that may promote division. "
                "Consider reframing with dignity and shared humanity in mind."
            )
        if scores.get("overall", 0) < 0.2:
            guidance.append(
                "This text scores low on flourishing dimensions. Consider how it could "
                "better serve compassion, dignity, cooperation, future generations, or nature."
            )
        scores["guidance"] = guidance
        return scores
    finally:
        await session.close()


# ---- Tool 3: Reframe Divisive Content ----

@mcp.tool()
async def reframe_divisive_content(text: str) -> dict:
    """Given divisive or harmful text, provide wisdom-based perspectives for reframing.

    Returns relevant wisdom from multiple traditions that address the underlying
    anti-patterns (tribalism, dehumanization, hatred, etc.) along with guidance.

    Args:
        text: The divisive or harmful text to reframe
    """
    service, session = await _get_service()
    try:
        scores = await service.flourishing_score(text)

        # Find wisdom that addresses relevant anti-patterns
        anti_pattern_keywords = [
            "hatred", "tribalism", "division", "dehumanization",
            "compassion", "unity", "dignity", "shared humanity",
        ]

        perspectives = []
        for keyword in anti_pattern_keywords[:4]:
            entries = await service.get_wisdom(topic=keyword, limit=2)
            perspectives.extend(entries)

        # Deduplicate
        seen = set()
        unique = []
        for e in perspectives:
            if e.id not in seen:
                seen.add(e.id)
                unique.append(e)

        return {
            "original_text": text,
            "flourishing_scores": scores,
            "divisiveness_detected": scores.get("divisiveness_flag", False),
            "wisdom_perspectives": [_entry_to_dict(e) for e in unique[:8]],
            "reframing_guidance": (
                "Every wisdom tradition teaches that what divides us is surface-level, "
                "while what unites us is fundamental. Consider: the Stoics taught that all humans "
                "share reason and dignity. Ubuntu philosophy says 'I am because we are.' "
                "The Upanishads declare the same self dwells in all beings. "
                "Buddhism teaches that all beings wish to be happy and free from suffering. "
                "Try reframing this through the lens of shared humanity and interconnection."
            ),
        }
    finally:
        await session.close()


# ---- Tool 4: Cross-Cultural Perspective ----

@mcp.tool()
async def get_cross_cultural_perspective(topic: str, limit: int = 6) -> list[dict]:
    """Get perspectives on a topic from multiple philosophical traditions.

    Shows how different cultures and philosophies approach the same question,
    revealing universal human wisdom.

    Args:
        topic: The topic to explore across traditions (e.g. "death", "justice", "love", "suffering")
        limit: Max number of traditions to include
    """
    service, session = await _get_service()
    try:
        entries = await service.get_cross_cultural_perspectives(topic, limit=limit)
        return [_entry_to_dict(e) for e in entries]
    finally:
        await session.close()


# ---- Tool 5: Flourishing Score ----

@mcp.tool()
async def flourishing_score(text: str) -> dict:
    """Score a decision, policy, or statement against human flourishing criteria.

    Returns scores (0-1) across five dimensions:
    - reduces_suffering: Does it alleviate pain and hardship?
    - respects_dignity: Does it honor human worth and autonomy?
    - promotes_cooperation: Does it foster unity and collaboration?
    - considers_future: Does it think about future generations?
    - honors_nature: Does it respect the natural world?

    Args:
        text: The text to score
    """
    service, session = await _get_service()
    try:
        return await service.flourishing_score(text)
    finally:
        await session.close()


# ---- Tool 6: Find Common Ground ----

@mcp.tool()
async def find_common_ground(theme: str) -> dict:
    """Show how different traditions converge on a universal theme.

    Demonstrates that wisdom traditions independently arrived at similar truths,
    revealing the deep structure of human ethical understanding.

    Args:
        theme: Universal theme slug (compassion, non-harm, dignity, stewardship, cooperation, golden-rule)
    """
    service, session = await _get_service()
    try:
        by_tradition = await service.find_common_ground(theme)
        return {
            "theme": theme,
            "traditions_count": len(by_tradition),
            "convergence": {
                trad: _entry_to_dict(entry) for trad, entry in by_tradition.items()
            },
            "insight": (
                f"Across {len(by_tradition)} independent traditions, "
                f"humanity converged on the same truth about '{theme}'. "
                "This convergence suggests these aren't cultural accidents but "
                "deep features of ethical reality."
            ),
        }
    finally:
        await session.close()


# ---- Tool 7: Get Practice / Meditation ----

@mcp.tool()
async def get_practice(situation: str) -> list[dict]:
    """Get a practical exercise, meditation, or daily practice for a life situation.

    Returns actionable wisdom — not just theory, but something to do.

    Args:
        situation: The life situation (e.g. "feeling angry", "grieving a loss", "making a hard decision")
    """
    service, session = await _get_service()
    try:
        entries = await service.get_wisdom(topic=situation, limit=5)
        return [
            {
                **_entry_to_dict(e),
                "practice_focus": e.practical_application,
            }
            for e in entries
        ]
    finally:
        await session.close()


# ---- Tool 8: Historical Lesson ----

@mcp.tool()
async def historical_lesson(pattern: str) -> list[dict]:
    """Find historical wisdom about recurring human patterns.

    Useful for understanding cycles of conflict, cooperation, rise and fall,
    and what past civilizations learned.

    Args:
        pattern: The pattern to explore (e.g. "tribalism", "empire", "corruption", "renewal")
    """
    service, session = await _get_service()
    try:
        entries = await service.get_wisdom(topic=pattern, limit=8)
        return [_entry_to_dict(e) for e in entries]
    finally:
        await session.close()


# ---- Tool 9: List Traditions ----

@mcp.tool()
async def list_traditions() -> list[dict]:
    """List all philosophical traditions in the wisdom repository.

    Returns available traditions with their descriptions, key figures,
    and core principles.
    """
    service, session = await _get_service()
    try:
        traditions = await service.list_traditions()
        return [
            {
                "slug": t.slug,
                "name": t.name,
                "origin_region": t.origin_region,
                "era": t.era,
                "description": t.description,
                "key_figures": t.key_figures,
                "core_principles": t.core_principles,
            }
            for t in traditions
        ]
    finally:
        await session.close()


# ---- Tool 10: List Themes ----

@mcp.tool()
async def list_themes() -> list[dict]:
    """List all universal themes that span philosophical traditions.

    Returns themes like compassion, non-harm, dignity, stewardship —
    the ethical universals that every major tradition independently discovered.
    """
    service, session = await _get_service()
    try:
        themes = await service.list_themes()
        return [
            {
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "anti_patterns": t.anti_patterns,
            }
            for t in themes
        ]
    finally:
        await session.close()
